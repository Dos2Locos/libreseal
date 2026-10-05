from django.core.management.base import BaseCommand
from django.utils import timezone

from api.models import (
    DynamicSecret,
    DynamicSecretLease,
    RotatingSecret,
    RotatingSecretCredential,
)

LIVE_ROTATION_STATUSES = [
    RotatingSecretCredential.ACTIVE,
    RotatingSecretCredential.EXPIRING,
    RotatingSecretCredential.REVOKING,
]


class Command(BaseCommand):
    help = (
        "List or remove dynamic secrets and rotating secrets migrated from "
        "Phase. LibreSeal cannot serve them nor revoke their credentials at "
        "the provider, and refuses to delete records of live credentials "
        "(including when deleting the app, environment or folder that holds "
        "them) until they are confirmed revoked."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--yes",
            action="store_true",
            help=(
                "Remove the listed records that have no live credentials. "
                "Without it, only lists them."
            ),
        )
        parser.add_argument(
            "--credentials-revoked",
            action="store_true",
            help=(
                "Confirm that live credentials (active leases, active rotating "
                "credentials) were revoked at the provider by other means; "
                "marks them revoked so their records can be removed too."
            ),
        )

    def _describe(self, kind, record, live):
        env = record.environment
        self.stdout.write(
            f"{kind}  {record.id}  {env.app.organisation.name}/{env.app.name}/"
            f"{env.name}{record.path}  {record.name}  live credentials: {live}"
        )

    def handle(self, *args, **options):
        related = "environment__app__organisation"
        items = []
        for secret in DynamicSecret.objects.filter(deleted_at=None).select_related(related):
            live = secret.leases.filter(status=DynamicSecretLease.ACTIVE)
            items.append(("dynamic", secret, live))
        for secret in RotatingSecret.objects.filter(deleted_at=None).select_related(related):
            live = secret.credentials.filter(status__in=LIVE_ROTATION_STATUSES)
            items.append(("rotating", secret, live))

        if not items:
            self.stdout.write("No dynamic or rotating secrets found.")
            return

        blocked = 0
        for kind, secret, live in items:
            count = live.count()
            blocked += bool(count)
            self._describe(kind, secret, count)

        if not options["yes"]:
            self.stdout.write("Re-run with --yes to remove them.")
            return

        revoke = options["credentials_revoked"]
        if blocked and not revoke:
            self.stdout.write(
                self.style.WARNING(
                    f"{blocked} records have live credentials that LibreSeal "
                    "cannot revoke. Revoke them at the provider, then re-run "
                    "with --yes --credentials-revoked."
                )
            )

        removed = 0
        for kind, secret, live in items:
            if live.exists():
                if not revoke:
                    continue
                live.update(status="revoked", revoked_at=timezone.now())
            secret.delete()
            removed += 1
        self.stdout.write(self.style.SUCCESS(f"Removed {removed} records."))
