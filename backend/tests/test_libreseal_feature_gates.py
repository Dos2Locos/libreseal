"""LibreSeal feature gates: no plan-based restrictions on core features, and
network access policies fail closed because they cannot be enforced."""

from unittest.mock import MagicMock, patch

import pytest
from graphql import GraphQLError


def _info(user=None):
    info = MagicMock()
    info.context.user = user or MagicMock()
    return info


# ---------------------------------------------------------------------------
# Core features are not gated by the stored plan
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("plan", ["FR", "PR", "EN"])
@patch("backend.graphene.mutations.access.user_has_permission", return_value=False)
@patch("backend.graphene.mutations.access.Organisation")
def test_custom_role_creation_reaches_rbac_on_any_plan(MockOrg, _perm, plan):
    """The only refusal must come from RBAC, never from the plan."""
    from backend.graphene.mutations.access import CreateCustomRoleMutation

    MockOrg.objects.get.return_value = MagicMock(plan=plan)
    MockOrg.FREE_PLAN = "FR"

    with pytest.raises(GraphQLError) as exc:
        CreateCustomRoleMutation.mutate(
            None, _info(), "Ops", "", "#fff", {}, organisation_id="org-1"
        )

    assert "permissions" in str(exc.value)
    assert "plan" not in str(exc.value)


@pytest.mark.parametrize("plan", ["FR", "PR", "EN"])
@patch("backend.graphene.mutations.teams.user_is_org_member", return_value=True)
@patch("backend.graphene.mutations.teams.user_has_permission", return_value=True)
@patch("backend.graphene.mutations.teams.Organisation")
def test_team_creation_passes_feature_gate_on_any_plan(MockOrg, _perm, _member, plan):
    """A blank name is rejected by validation, which runs after the feature
    gate: reaching it proves no plan restriction applied."""
    from backend.graphene.mutations.teams import CreateTeamMutation

    MockOrg.objects.get.return_value = MagicMock(plan=plan)

    with pytest.raises(GraphQLError, match="cannot be blank"):
        # Bypass @transaction.atomic: these unit tests run without a database.
        CreateTeamMutation.mutate.__func__.__wrapped__(
            CreateTeamMutation, None, _info(), organisation_id="org-1", name=" "
        )


# ---------------------------------------------------------------------------
# Network access policies: configuration refused, enforcement fails closed
# ---------------------------------------------------------------------------


@patch("backend.graphene.mutations.access.Organisation")
def test_create_network_policy_refused(MockOrg):
    from backend.graphene.mutations.access import CreateNetworkAccessPolicyMutation

    with pytest.raises(GraphQLError, match="not available in LibreSeal"):
        CreateNetworkAccessPolicyMutation.mutate(
            None, _info(), "office", "10.0.0.0/8", False, "org-1"
        )
    MockOrg.objects.get.assert_not_called()


def test_update_network_policy_refused():
    from backend.graphene.mutations.access import UpdateNetworkAccessPolicyMutation

    with pytest.raises(GraphQLError, match="not available in LibreSeal"):
        UpdateNetworkAccessPolicyMutation.mutate(None, _info(), [MagicMock()])


def test_assigning_network_policies_refused():
    from backend.graphene.mutations.access import UpdateAccountNetworkAccessPolicies

    account_input = MagicMock(policy_ids=["p1"])
    with pytest.raises(GraphQLError, match="not available in LibreSeal"):
        UpdateAccountNetworkAccessPolicies.mutate(
            None, _info(), [account_input], "org-1"
        )


@patch("api.utils.access.network_policies.NetworkAccessPolicy")
def test_account_with_policy_is_denied(MockPolicy):
    from api.utils.access.network_policies import network_access_denied

    account = MagicMock()
    account.network_policies.exists.return_value = True

    assert network_access_denied(MagicMock(), account) is True


@patch("api.utils.access.network_policies.NetworkAccessPolicy")
def test_global_policy_denies_everyone(MockPolicy):
    from api.utils.access.network_policies import network_access_denied

    account = MagicMock()
    account.network_policies.exists.return_value = False
    MockPolicy.objects.filter.return_value.exists.return_value = True

    assert network_access_denied(MagicMock(), account) is True


@patch("api.utils.access.network_policies.NetworkAccessPolicy")
def test_no_policies_allows(MockPolicy):
    from api.utils.access.network_policies import network_access_denied

    account = MagicMock()
    account.network_policies.exists.return_value = False
    MockPolicy.objects.filter.return_value.exists.return_value = False

    assert network_access_denied(MagicMock(), account) is False


def test_no_organisation_allows():
    from api.utils.access.network_policies import network_access_denied

    assert network_access_denied(None, None) is False


@pytest.mark.parametrize("denied,expected", [(True, False), (False, True)])
@patch("api.utils.access.middleware.network_access_denied")
def test_rest_permission_uses_fail_closed_check(mock_denied, denied, expected):
    from api.utils.access.middleware import IsIPAllowed

    mock_denied.return_value = denied
    sa = MagicMock()
    request = MagicMock()
    request.auth = {"org_member": None, "service_account": sa}

    assert IsIPAllowed().has_permission(request, None) is expected
    mock_denied.assert_called_once_with(sa.organisation, sa)


@patch("backend.graphene.middleware.network_access_denied", return_value=True)
@patch("backend.graphene.middleware.OrganisationMember")
@patch("backend.graphene.middleware.Organisation")
def test_graphql_middleware_fails_closed(MockOrg, MockOM, _denied):
    from backend.graphene.middleware import (
        IPWhitelistMiddleware,
        NetworkPolicyUnenforceableError,
    )

    info = _info()
    info.context.user.is_authenticated = True
    next_ = MagicMock()

    with pytest.raises(NetworkPolicyUnenforceableError):
        IPWhitelistMiddleware().resolve(next_, None, info, organisation_id="org-1")
    next_.assert_not_called()


@patch("backend.graphene.middleware.network_access_denied", return_value=False)
@patch("backend.graphene.middleware.OrganisationMember")
@patch("backend.graphene.middleware.Organisation")
def test_graphql_middleware_passes_without_policies(MockOrg, MockOM, _denied):
    from backend.graphene.middleware import IPWhitelistMiddleware

    info = _info()
    info.context.user.is_authenticated = True
    next_ = MagicMock(return_value="ok")

    assert (
        IPWhitelistMiddleware().resolve(next_, None, info, organisation_id="org-1")
        == "ok"
    )
