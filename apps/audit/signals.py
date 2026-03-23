"""
Signal handlers for NIS2 audit events.

authz.group.changed: fires when a user's group memberships actually change.

Strategy:
  - pre_remove:  snapshot the full group set into thread-local storage.
  - post_remove: schedule a deferred emit via on_commit for standalone removes.
                 If post_add fires before commit (sync case), it cancels this
                 by adding the user pk to _tl.post_add_handled.
  - post_add:    if a remove snapshot exists, compute net diff:
                 - groups unchanged (no-op sync) → cancel deferred emit, skip
                 - groups changed → cancel deferred emit, emit combined diff
                 If no snapshot, standalone add → emit immediately.

Using on_commit for standalone removes ensures we don't emit during no-op syncs:
the sync removes + re-adds happen in the same transaction, so by commit time
post_add has already fired and cancelled the deferred emit.
"""

import logging
import threading

from django.contrib.auth.models import Group, User
from django.db import transaction
from django.db.models.signals import m2m_changed
from django.dispatch import receiver

audit_logger = logging.getLogger("audit")
_tl = threading.local()


def _emit_group_change(username, added_pks, removed_pks):
    added_names = (
        list(Group.objects.filter(pk__in=added_pks).values_list("name", flat=True))
        if added_pks else []
    )
    removed_names = (
        list(Group.objects.filter(pk__in=removed_pks).values_list("name", flat=True))
        if removed_pks else []
    )
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


@receiver(m2m_changed, sender=User.groups.through, dispatch_uid="audit.on_user_groups_changed")
def on_user_groups_changed(sender, instance, action, pk_set, **kwargs):
    if action == "pre_remove" and pk_set:
        _tl.user_pk = instance.pk
        _tl.groups_before = set(instance.groups.values_list("pk", flat=True))
        _tl.removed_pks = frozenset(pk_set)
        _tl.post_add_handled = set()  # reset at start of each operation

    elif action == "post_remove":
        if getattr(_tl, "user_pk", None) != instance.pk:
            return
        # Snapshot owned. Defer standalone-remove emit to on_commit.
        # post_add (if it fires) will add instance.pk to _tl.post_add_handled
        # before commit, cancelling this callback.
        user_pk = instance.pk
        username = instance.username
        removed_pks = getattr(_tl, "removed_pks", frozenset())
        # Capture the set by reference before the closure definition
        if not hasattr(_tl, "post_add_handled"):
            _tl.post_add_handled = set()
        handled_ref = _tl.post_add_handled

        @transaction.on_commit
        def maybe_emit_standalone_remove():
            if user_pk in handled_ref:
                handled_ref.discard(user_pk)
                return
            _emit_group_change(username, added_pks=set(), removed_pks=removed_pks)

    elif action == "post_add":
        groups_before = getattr(_tl, "groups_before", None)

        if groups_before is not None and getattr(_tl, "user_pk", None) == instance.pk:
            # Sync pattern (remove preceded this add). Compute net diff.
            groups_after = set(instance.groups.values_list("pk", flat=True))
            user_pk = instance.pk
            username = instance.username
            _tl.user_pk = None
            _tl.groups_before = None
            _tl.removed_pks = None

            # Mark as handled so the on_commit callback from post_remove skips.
            if not hasattr(_tl, "post_add_handled"):
                _tl.post_add_handled = set()
            _tl.post_add_handled.add(user_pk)

            if groups_before == groups_after:
                return  # no-op sync — deferred emit cancelled

            added_pks = groups_after - groups_before
            removed_pks = groups_before - groups_after
            _emit_group_change(username, added_pks=added_pks, removed_pks=removed_pks)

        else:
            # Standalone add.
            if not hasattr(_tl, "post_add_handled"):
                _tl.post_add_handled = set()
            added_pks = pk_set or set()
            if added_pks:
                _emit_group_change(instance.username, added_pks=added_pks, removed_pks=set())
