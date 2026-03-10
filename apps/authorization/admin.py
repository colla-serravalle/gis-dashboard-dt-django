from django.contrib import admin
from .models import Service


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("name", "app_label", "is_active", "group_list")
    list_filter = ("is_active",)
    filter_horizontal = ("allowed_groups",)

    @admin.display(description="Allowed Groups")
    def group_list(self, obj):
        return ", ".join(g.name for g in obj.allowed_groups.all())
