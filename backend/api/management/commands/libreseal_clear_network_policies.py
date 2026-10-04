from django.core.management.base import BaseCommand

from api.models import NetworkAccessPolicy


class Command(BaseCommand):
    help = (
        "List or delete network access policies. LibreSeal cannot enforce "
        "them, so accounts they apply to are denied access (fail closed)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--organisation",
            help="Only act on policies of this organisation (name or ID).",
        )
        parser.add_argument(
            "--yes",
            action="store_true",
            help="Delete the listed policies. Without it, only lists them.",
        )

    def handle(self, *args, **options):
        policies = NetworkAccessPolicy.objects.select_related("organisation")
        org = options.get("organisation")
        if org:
            policies = policies.filter(organisation__name=org) | policies.filter(
                organisation__id__iexact=org
            )

        policies = list(policies)
        if not policies:
            self.stdout.write("No network access policies found.")
            return

        for policy in policies:
            scope = "global" if policy.is_global else "per-account"
            self.stdout.write(
                f"{policy.id}  {policy.organisation.name}  {policy.name}  ({scope})"
            )

        if not options["yes"]:
            self.stdout.write("Re-run with --yes to delete these policies.")
            return

        for policy in policies:
            policy.delete()
        self.stdout.write(self.style.SUCCESS(f"Deleted {len(policies)} policies."))
