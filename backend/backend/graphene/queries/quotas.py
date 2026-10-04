from api.utils.access.permissions import user_is_org_member
from api.models import (
    App,
    OrganisationMember,
    OrganisationMemberInvite,
    ServiceAccount,
)
from backend.quotas import LIBRESEAL_LIMITS
from django.utils import timezone


def build_plan_detail(organisation):
    """Usage counters plus LibreSeal limits (all unlimited) for an organisation."""
    users = (
        OrganisationMember.objects.filter(
            organisation=organisation, deleted_at=None
        ).count()
        + OrganisationMemberInvite.objects.filter(
            organisation=organisation,
            valid=True,
            expires_at__gte=timezone.now(),
        ).count()
    )
    service_accounts = ServiceAccount.objects.filter(
        organisation=organisation, deleted_at=None
    ).count()

    return {
        **LIBRESEAL_LIMITS,
        "seat_limit": None,
        "seats_used": {
            "users": users,
            "service_accounts": service_accounts,
            "total": users + service_accounts,
        },
        "app_count": App.objects.filter(
            organisation=organisation, deleted_at=None
        ).count(),
    }


def resolve_organisation_plan(self, info, organisation_id):
    if user_is_org_member(info.context.user, organisation_id):
        from api.models import Organisation

        organisation = Organisation.objects.get(id=organisation_id)
        return build_plan_detail(organisation)
