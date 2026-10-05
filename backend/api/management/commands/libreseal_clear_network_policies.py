import getpass
import uuid

from django.core.management.base import BaseCommand, CommandError

from api.models import NetworkAccessPolicy, Organisation
from api.utils.audit_logging import log_audit_event

COMMAND = "libreseal_clear_network_policies"


def _os_user():
    try:
        return getpass.getuser()
    except Exception:
        return ""


class Command(BaseCommand):
    help = (
        "List or delete network access policies, e.g. to recover from a "
        "lock-out. Deletions are recorded in each organisation's audit log."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--organisation",
            help=(
                "Only act on policies of this organisation (ID or name)."
            ),
        )
        parser.add_argument(
            "--yes",
            action="store_true",
            help="Delete the listed policies. Without it, only lists them.",
        )

    def _resolve_organisation(self, value):
        if _is_uuid(value):
            org = Organisation.objects.filter(id=value).first()
            if org is not None:
                return org
        org = Organisation.objects.filter(name=value).first()  # names are unique
        if org is None:
            raise CommandError(f"No organisation with ID or name '{value}'.")
        return org

    def handle(self, *args, **options):
        policies = NetworkAccessPolicy.objects.select_related("organisation")
        if options.get("organisation"):
            org = self._resolve_organisation(options["organisation"])
            policies = policies.filter(organisation=org)

        policies = list(policies)
        if not policies:
            self.stdout.write("No network access policies found.")
            return

        for policy in policies:
            scope = "global" if policy.is_global else "per-account"
            self.stdout.write(
                f"{policy.id}  {policy.organisation.id}  {policy.organisation.name}  "
                f"{policy.name}  ({scope})"
            )

        if not options["yes"]:
            self.stdout.write("Re-run with --yes to delete these policies.")
            return

        os_user = _os_user()
        for policy in policies:
            policy_id, policy_name, org = policy.id, policy.name, policy.organisation
            policy.delete()
            log_audit_event(
                organisation=org,
                event_type="D",
                resource_type="policy",
                resource_id=policy_id,
                # AuditEvent actors are users or service accounts; a server
                # operator is recorded as an anonymous user with metadata.
                actor_type="user",
                actor_id="",
                actor_metadata={
                    "username": f"Server administrator (manage.py {COMMAND})",
                    "source": "management_command",
                    "command": COMMAND,
                    "os_user": os_user,
                },
                resource_metadata={"name": policy_name},
                description=(
                    f"Deleted network access policy '{policy_name}' from the "
                    "server command line"
                ),
            )
        self.stdout.write(self.style.SUCCESS(f"Deleted {len(policies)} policies."))


def _is_uuid(value):
    try:
        uuid.UUID(str(value))
        return True
    except ValueError:
        return False
