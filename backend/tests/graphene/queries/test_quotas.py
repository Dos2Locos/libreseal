"""resolve_organisation_plan reporting in LibreSeal.

The frontend computes availableSeats = seatLimit - seatsUsed to gate member
invites. LibreSeal has no seat cap, so seat_limit and all max_* limits must be
None (unlimited) whatever plan value is stored on the organisation.
"""

from unittest.mock import MagicMock, patch

import pytest


_M = "backend.graphene.queries.quotas"


def _info():
    info = MagicMock()
    info.context.user = MagicMock()
    return info


@pytest.mark.parametrize("plan", ["FR", "PR", "EN"])
def test_plan_detail_is_unlimited(plan):
    from backend.graphene.queries.quotas import resolve_organisation_plan

    org = MagicMock(plan=plan)

    with patch(f"{_M}.user_is_org_member", return_value=True), patch(
        "api.models.Organisation"
    ) as MockOrg, patch(f"{_M}.OrganisationMember") as MockMember, patch(
        f"{_M}.OrganisationMemberInvite"
    ) as MockInvite, patch(f"{_M}.ServiceAccount") as MockSA, patch(
        f"{_M}.App"
    ) as MockApp:
        MockOrg.objects.get.return_value = org
        MockMember.objects.filter.return_value.count.return_value = 2
        MockInvite.objects.filter.return_value.count.return_value = 1
        MockSA.objects.filter.return_value.count.return_value = 7
        MockApp.objects.filter.return_value.count.return_value = 4

        detail = resolve_organisation_plan(None, _info(), organisation_id="org-1")

    assert detail["name"] == "LibreSeal"
    assert detail["seat_limit"] is None
    assert detail["max_users"] is None
    assert detail["max_apps"] is None
    assert detail["max_envs_per_app"] is None
    assert detail["seats_used"] == {"users": 3, "service_accounts": 7, "total": 10}
    assert detail["app_count"] == 4


def test_non_member_gets_nothing():
    from backend.graphene.queries.quotas import resolve_organisation_plan

    with patch(f"{_M}.user_is_org_member", return_value=False):
        assert resolve_organisation_plan(None, _info(), organisation_id="x") is None


def test_plan_detail_does_not_share_state_between_calls():
    from backend.graphene.queries.quotas import build_plan_detail
    from backend.quotas import LIBRESEAL_LIMITS

    with patch(f"{_M}.OrganisationMember"), patch(
        f"{_M}.OrganisationMemberInvite"
    ), patch(f"{_M}.ServiceAccount"), patch(f"{_M}.App"):
        build_plan_detail(MagicMock())

    assert "seats_used" not in LIBRESEAL_LIMITS
