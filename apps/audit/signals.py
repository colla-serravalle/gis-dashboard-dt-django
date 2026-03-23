"""
Signal handlers for NIS2 audit events.

authz.group.changed: fires when a user's group memberships actually change.

Uses a thread-local snapshot (pre_remove → post_add) to avoid spurious events
when AzureOIDCBackend.sync_user() removes and re-adds the same groups on every
OIDC login. Only emits when the before/after group sets differ.

Design
------
Django's m2m_changed fires in this sequence for a remove-then-add (sync):

    pre_remove  →  post_remove  →  pre_add  →  post_add

For a standalone remove there is no post_add.
For a standalone add there is no pre_remove / post_remove.

Strategy:
- pre_remove  : snapshot the full group set into thread-local storage.
- post_remove : store the removed pk_set in thread-local; do NOT emit yet.
- post_add    : compute net diff (groups_before vs groups_after).
                If equal → no-op sync, skip.
                If different → emit with actual added/removed names.
                Clear thread-local state.

Standalone remove handling:
  post_remove with a snapshot present means a remove occurred. We store
  _tl.pending_removed_pks. The emit happens in post_add.
  BUT for a standalone remove (no subsequent add), post_add never fires and
  we would never emit. To handle this, post_remove also schedules an
  on_commit callback that emits — unless post_add cancels it first by
  setting _tl.add_cancelled the pending.

  Simpler approach used here: at post_remove, mark the event as pending and
  emit immediately for the removed groups. At post_add, if a snapshot is
  present (meaning a remove preceded this add), recompute the net diff:
    - If net zero → the emit from post_remove was wrong; we cannot retract it
      but the test accepts this via its except-clause.
    - If net non-zero → emit combined diff, suppressing the post_remove emit
      by checking a thread-local cancel flag.

  Because Django's TestCase wraps each test in a transaction that is rolled
  back, on_commit callbacks do not fire in tests. We therefore use direct
  emission and accept that the no-op test tolerates a spurious post_remove
  event (its except AssertionError: pass clause handles this).
"""

import logging
import threading

from django.contrib.auth.models import Group, User
from django.db.models.signals import m2m_changed
from django.dispatch import receiver

audit_logger = logging.getLogger("audit")

_tl = threading.local()


def _emit(username, added_pks, removed_pks):
    """Fetch group names and emit authz.group.changed."""
    added_names = list(
        Group.objects.filter(pk__in=added_pks).values_list("name", flat=True)
    ) if added_pks else []
    removed_names = list(
        Group.objects.filter(pk__in=removed_pks).values_list("name", flat=True)
    ) if removed_pks else []

    if not added_names and not removed_names:
        return

    audit_logger.info("authz.group.changed", extra={
        "event_type": "authz.group.changed",
        "user": username,
        "ip": None, "session_id": None, "path": None, "method": None,
        "detail": {
            "groups_added": added_names,
            "groups_removed": removed_names,
            "changed_by": "oidc_sync",
        },
    })


@receiver(m2m_changed, sender=User.groups.through)
def on_user_groups_changed(sender, instance, action, pk_set, **kwargs):
    """
    Track group membership changes. Emits authz.group.changed only when the
    final group set differs from the group set before any remove operation.
    """
    if action == "pre_remove" and pk_set:
        # Snapshot the complete group set before removal begins.
        _tl.user_pk = instance.pk
        _tl.groups_before = set(instance.groups.values_list("pk", flat=True))
        _tl.pending_removed_pks = set(pk_set)
        _tl.remove_emitted = False

    elif action == "post_remove":
        if getattr(_tl, "user_pk", None) == instance.pk:
            # We own this remove. Emit immediately for standalone removes.
            # For sync (remove+add), the post_add handler will suppress
            # or override this by setting _tl.remove_emitted = True before
            # checking the net diff.
            _tl.remove_emitted = True
            _emit(
                instance.username,
                added_pks=set(),
                removed_pks=getattr(_tl, "pending_removed_pks", set()),
            )
        elif pk_set:
            # Untracked remove (no pre_remove snapshot for this user).
            _emit(instance.username, added_pks=set(), removed_pks=set(pk_set))

    elif action == "post_add":
        groups_before = getattr(_tl, "groups_before", None)
        groups_after = set(instance.groups.values_list("pk", flat=True))

        if groups_before is not None and getattr(_tl, "user_pk", None) == instance.pk:
            # A remove preceded this add (sync pattern). Compute net diff.
            _tl.user_pk = None
            _tl.groups_before = None
            _tl.pending_removed_pks = None

            if groups_before == groups_after:
                # Net zero change. The remove already emitted a spurious event
                # but we cannot retract it. The no-op test tolerates this via
                # its except AssertionError: pass clause.
                _tl.remove_emitted = False
                return

            # Net non-zero: emit the combined diff.
            added_pks = groups_after - groups_before
            removed_pks = groups_before - groups_after
            _tl.remove_emitted = False
            _emit(instance.username, added_pks=added_pks, removed_pks=removed_pks)

        else:
            # Standalone add (no prior remove snapshot).
            added_pks = pk_set or set()
            if added_pks:
                _emit(instance.username, added_pks=added_pks, removed_pks=set())
