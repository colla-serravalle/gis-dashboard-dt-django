from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group
from apps.authorization.models import Service


# URL namespace → group names mapping for this project.
# Groups are created if they don't exist.
# Edit this list to add or change service definitions.
SERVICE_DEFINITIONS = [
    {
        "name": "Dashboard",
        "app_label": "core",
        "description": "Main dashboard and home page",
        "groups": ["dashboard_users", "managers"],
    },
    {
        "name": "Reports",
        "app_label": "reports",
        "description": "Report di sopralluogo per interventi di manutenzione.",
        "groups": ["reports_users", "managers"],
        "icon_class": "fa-solid fa-file-invoice",
        "list_url_name": "reports:report_list",
        "display_order": 1,
    },
    {
        "name": "Reports API",
        "app_label": "reports_api",
        "description": "Reports JSON API endpoints",
        "groups": ["reports_users", "managers"],
    },
    {
        "name": "Segnalazioni",
        "app_label": "segnalazioni",
        "description": "Pannello di gestione delle segnalazioni ricevute.",
        "groups": ["segnalazioni_users", "managers"],
        "icon_class": "fa-solid fa-triangle-exclamation",
        "list_url_name": "segnalazioni:segnalazioni_list",
        "display_order": 2,
    },
    {
        "name": "Segnalazioni API",
        "app_label": "segnalazioni_api",
        "description": "Segnalazioni JSON API endpoints",
        "groups": ["segnalazioni_users", "managers"],
    },
    {
        "name": "Profiles",
        "app_label": "profiles",
        "description": "User profile pages",
        "groups": ["dashboard_users", "reports_users", "managers"],
    },
]


class Command(BaseCommand):
    help = "Create or update Service records and their group associations"

    def handle(self, *args, **options):
        for svc_def in SERVICE_DEFINITIONS:
            service, created = Service.objects.update_or_create(
                app_label=svc_def["app_label"],
                defaults={
                    "name": svc_def["name"],
                    "description": svc_def.get("description", ""),
                    "is_active": True,
                    "icon_class": svc_def.get("icon_class", ""),
                    "list_url_name": svc_def.get("list_url_name", ""),
                    "display_order": svc_def.get("display_order", 0),
                },
            )
            groups = []
            for group_name in svc_def.get("groups", []):
                group, group_created = Group.objects.get_or_create(name=group_name)
                groups.append(group)
                if group_created:
                    self.stdout.write(f"  Created group: {group_name}")
            service.allowed_groups.set(groups)

            status = "Created" if created else "Updated"
            self.stdout.write(self.style.SUCCESS(
                f"{status}: {service.name} ({service.app_label}) "
                f"— groups: {', '.join(g.name for g in groups)}"
            ))
