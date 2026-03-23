from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User

from apps.audit.utils import emit_audit_event


class AuditUserAdmin(UserAdmin):
    """Extends the built-in UserAdmin to emit audit events on user saves."""

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if change:
            emit_audit_event(request, "admin.user.changed", detail={
                "user_changed": obj.username,
                "changed_by": request.user.username,
                "fields": list(form.changed_data),
            })


admin.site.unregister(User)
admin.site.register(User, AuditUserAdmin)
