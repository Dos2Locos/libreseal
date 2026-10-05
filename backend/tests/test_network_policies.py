"""Clean-room network access policy verifier (api.utils.access.network_policies)."""

from unittest.mock import MagicMock, patch

import pytest

from api.utils.access import network_policies as np


@pytest.mark.parametrize(
    "ip,allowed,expected",
    [
        ("10.1.2.3", "10.0.0.0/8", True),
        ("192.0.2.10", "10.0.0.0/8", False),
        ("10.1.2.3", "192.168.1.1, 10.1.2.3", True),  # single IP entry
        ("10.1.2.4", "10.1.2.3", False),
        ("10.1.2.3", " 172.16.0.0/12 ,10.1.0.0/16 ", True),  # whitespace
        ("10.1.2.3", "10.1.2.0/24", True),
        ("10.1.2.3", "10.1.2.3/24", True),  # host bits set: non-strict
        ("2001:db8::1", "2001:db8::/32", True),
        ("2001:db8::1", "2001:db9::/32", False),
        ("::ffff:10.1.2.3", "10.0.0.0/8", True),  # IPv4-mapped IPv6
        ("10.1.2.3", "::/0", False),  # IPv6 range never matches IPv4
        ("0.0.0.0", "0.0.0.0/0", True),
        ("10.1.2.3", "", False),
        ("10.1.2.3", "not-an-ip, 10.0.0.0/33", False),  # invalid entries grant nothing
        ("10.1.2.3", "garbage, 10.0.0.0/8", True),  # valid entries still apply
        (None, "0.0.0.0/0", False),  # unknown client IP fails closed
        ("", "0.0.0.0/0", False),
        ("not-an-ip", "0.0.0.0/0", False),
    ],
)
def test_ip_matches(ip, allowed, expected):
    assert np.ip_matches(ip, allowed) is expected


def test_validate_allowed_ips_accepts_valid_lists():
    np.validate_allowed_ips("10.0.0.0/8, 192.168.1.10, 2001:db8::/48")


@pytest.mark.parametrize("value", ["", "  ,  ", "10.0.0.0/8, nope", "300.1.1.1", "10.0.0.0/33"])
def test_validate_allowed_ips_rejects_invalid(value):
    with pytest.raises(ValueError):
        np.validate_allowed_ips(value)


def _policy(pid, allowed):
    return MagicMock(id=pid, allowed_ips=allowed)


def _account(policies):
    account = MagicMock()
    account.network_policies.all.return_value = policies
    account.network_policies.exists.return_value = bool(policies)
    return account


@pytest.fixture
def enforced():
    with patch.object(np, "feature_enabled", return_value=True):
        yield


@patch("api.utils.access.network_policies.NetworkAccessPolicy")
def test_allowed_ip_passes(MockPolicy, enforced):
    MockPolicy.objects.filter.return_value = []
    account = _account([_policy("p1", "10.0.0.0/8")])
    assert np.network_access_denied(MagicMock(), account, "10.1.2.3") is False


@patch("api.utils.access.network_policies.NetworkAccessPolicy")
def test_disallowed_ip_denied(MockPolicy, enforced):
    MockPolicy.objects.filter.return_value = []
    account = _account([_policy("p1", "10.0.0.0/8")])
    assert np.network_access_denied(MagicMock(), account, "192.0.2.10") is True


@patch("api.utils.access.network_policies.NetworkAccessPolicy")
def test_global_policy_applies_to_accounts_without_own_policies(MockPolicy, enforced):
    MockPolicy.objects.filter.return_value = [_policy("g1", "10.0.0.0/8")]
    account = _account([])
    assert np.network_access_denied(MagicMock(), account, "192.0.2.10") is True
    assert np.network_access_denied(MagicMock(), account, "10.9.9.9") is False


@patch("api.utils.access.network_policies.NetworkAccessPolicy")
def test_any_applicable_policy_may_allow(MockPolicy, enforced):
    MockPolicy.objects.filter.return_value = [_policy("g1", "172.16.0.0/12")]
    account = _account([_policy("p1", "10.0.0.0/8")])
    assert np.network_access_denied(MagicMock(), account, "172.16.5.5") is False


@patch("api.utils.access.network_policies.NetworkAccessPolicy")
def test_no_policies_allows(MockPolicy, enforced):
    MockPolicy.objects.filter.return_value = []
    assert np.network_access_denied(MagicMock(), _account([]), "192.0.2.10") is False


@patch("api.utils.access.network_policies.NetworkAccessPolicy")
def test_malformed_only_policy_denies(MockPolicy, enforced):
    MockPolicy.objects.filter.return_value = []
    account = _account([_policy("p1", "not-an-ip")])
    assert np.network_access_denied(MagicMock(), account, "10.1.2.3") is True


@patch("api.utils.access.network_policies.NetworkAccessPolicy")
def test_missing_client_ip_denied_when_policies_apply(MockPolicy, enforced):
    MockPolicy.objects.filter.return_value = []
    account = _account([_policy("p1", "0.0.0.0/0")])
    assert np.network_access_denied(MagicMock(), account, None) is True


def test_no_organisation_allows():
    assert np.network_access_denied(None, None, "10.1.2.3") is False


@patch("api.utils.access.network_policies.NetworkAccessPolicy")
def test_disabled_feature_fails_closed(MockPolicy):
    with patch.object(np, "feature_enabled", return_value=False):
        account = _account([_policy("p1", "10.0.0.0/8")])
        assert np.network_access_denied(MagicMock(), account, "10.1.2.3") is True
        assert np.denial_message() == np.UNENFORCEABLE_MESSAGE


# ---------------------------------------------------------------------------
# GraphQL write-time validation
# ---------------------------------------------------------------------------

from graphql import GraphQLError  # noqa: E402


def _info():
    info = MagicMock()
    info.context.user = MagicMock()
    return info


@patch("backend.graphene.mutations.access.NetworkAccessPolicy")
@patch("backend.graphene.mutations.access.OrganisationMember")
@patch("backend.graphene.mutations.access.user_has_permission", return_value=True)
@patch("backend.graphene.mutations.access.Organisation")
@patch("backend.graphene.mutations.access.feature_enabled", return_value=True)
def test_create_policy_rejects_invalid_entries(_f, MockOrg, _perm, _om, MockPolicy):
    from backend.graphene.mutations.access import CreateNetworkAccessPolicyMutation

    with pytest.raises(GraphQLError, match="Invalid IP address or CIDR range: nope"):
        CreateNetworkAccessPolicyMutation.mutate(
            None, _info(), "office", "10.0.0.0/8, nope", False, "org-1"
        )
    MockPolicy.objects.create.assert_not_called()


@patch("backend.graphene.mutations.access.NetworkAccessPolicy")
@patch("backend.graphene.mutations.access.user_has_permission", return_value=True)
@patch("backend.graphene.mutations.access.OrganisationMember")
@patch("backend.graphene.mutations.access.feature_enabled", return_value=True)
def test_update_policy_rejects_invalid_entries(_f, _om, _perm, MockPolicy):
    from backend.graphene.mutations.access import UpdateNetworkAccessPolicyMutation

    policy = MagicMock(allowed_ips="10.0.0.0/8")
    MockPolicy.objects.get.return_value = policy
    policy_input = MagicMock(id="p1", allowed_ips="999.1.1.1", is_global=None)
    policy_input.name = None
    with pytest.raises(GraphQLError, match="Invalid IP address"):
        UpdateNetworkAccessPolicyMutation.mutate(None, _info(), [policy_input])
    policy.save.assert_not_called()


# ---------------------------------------------------------------------------
# GraphQL middleware: enforcement beyond `organisation_id`
# ---------------------------------------------------------------------------

from backend.graphene import middleware as mw  # noqa: E402


class _Request:
    def __init__(self):
        self.user = MagicMock(is_authenticated=True, userId="u1")
        self.session = {}


def _gql_info(request=None):
    info = MagicMock()
    info.context = request or _Request()
    return info


def _org(name):
    org = MagicMock()
    org.name = name
    return org


@pytest.fixture
def gql_env():
    """Patch org lookup and policy decision: org-blocked denies, others allow."""
    orgs = {"org-ok": _org("ok"), "org-blocked": _org("blocked")}
    with patch.object(mw, "Organisation") as MockOrg, patch.object(
        mw, "OrganisationMember"
    ), patch.object(mw, "feature_enabled", return_value=True), patch.object(
        mw, "network_access_denied", side_effect=lambda org, *_: org.name == "blocked"
    ) as denied, patch.object(
        mw.IPWhitelistMiddleware, "get_client_ip", return_value="192.0.2.10"
    ):
        MockOrg.objects.filter.side_effect = lambda id: MagicMock(
            first=MagicMock(return_value=orgs.get(id))
        )
        yield denied


@pytest.mark.parametrize(
    "kwargs,resolved",
    [
        ({"env_id": "e1"}, "org-blocked"),  # e.g. secrets(envId), folders(envId)
        ({"secret_id": "s1"}, "org-blocked"),  # e.g. secretHistory(secretId)
        ({"folder_id": "f1"}, "org-blocked"),  # deleteSecretFolder
    ],
)
def test_graphql_denies_fields_without_organisation_id(gql_env, kwargs, resolved):
    next_ = MagicMock()
    with patch.object(mw, "resolve_org_id", return_value=resolved):
        with pytest.raises(mw.IPRestrictedError):
            mw.IPWhitelistMiddleware().resolve(next_, None, _gql_info(), **kwargs)
    next_.assert_not_called()


def test_graphql_denies_bare_id_mutation(gql_env):
    next_ = MagicMock()
    with patch.object(mw, "_model_for_mutation", return_value="Secret"), patch.object(
        mw, "resolve_via_model", return_value="org-blocked"
    ):
        with pytest.raises(mw.IPRestrictedError):
            mw.IPWhitelistMiddleware().resolve(next_, None, _gql_info(), id="s1")
    next_.assert_not_called()


def test_graphql_bulk_ids_check_every_organisation(gql_env):
    """A bulk mutation mixing resources of an allowed and a denied
    organisation is denied, not just checked against the first item."""
    next_ = MagicMock()
    with patch.object(mw, "_model_for_mutation", return_value="Secret"), patch.object(
        mw, "resolve_orgs_via_model", return_value={"org-ok", "org-blocked"}
    ) as bulk:
        with pytest.raises(mw.IPRestrictedError):
            mw.IPWhitelistMiddleware().resolve(
                next_, None, _gql_info(), ids=["s-ok", "s-blocked"]
            )
    assert bulk.call_args.args[1] == ["s-ok", "s-blocked"]
    next_.assert_not_called()


def test_graphql_input_list_checks_every_item(gql_env):
    """updateNetworkAccessPolicy(policyInputs) cannot widen a policy of a
    denied organisation by putting an allowed one first."""
    next_ = MagicMock()
    inputs = [{"id": "p-ok"}, {"id": "p-blocked"}]
    with patch.object(
        mw, "_model_for_mutation", return_value="NetworkAccessPolicy"
    ), patch.object(
        mw,
        "resolve_via_model",
        side_effect=lambda model, pk, cache: {"p-ok": "org-ok", "p-blocked": "org-blocked"}[pk],
    ):
        with pytest.raises(mw.IPRestrictedError):
            mw.IPWhitelistMiddleware().resolve(
                next_, None, _gql_info(), policy_inputs=inputs
            )
    next_.assert_not_called()


def test_graphql_allows_when_policies_allow(gql_env):
    next_ = MagicMock(return_value="ok")
    with patch.object(mw, "resolve_org_id", return_value="org-ok"):
        assert (
            mw.IPWhitelistMiddleware().resolve(next_, None, _gql_info(), env_id="e1")
            == "ok"
        )


def test_graphql_unknown_organisation_passes_to_resolver(gql_env):
    next_ = MagicMock(return_value="resolver decides")
    assert (
        mw.IPWhitelistMiddleware().resolve(
            next_, None, _gql_info(), organisation_id="org-missing"
        )
        == "resolver decides"
    )


def test_graphql_decision_cached_per_request(gql_env):
    request = _Request()
    next_ = MagicMock(return_value="ok")
    middleware = mw.IPWhitelistMiddleware()
    for _ in range(3):
        middleware.resolve(next_, None, _gql_info(request), organisation_id="org-ok")
    assert gql_env.call_count == 1


def test_graphql_fields_without_arguments_are_not_checked(gql_env):
    next_ = MagicMock(return_value="ok")
    assert mw.IPWhitelistMiddleware().resolve(next_, None, _gql_info()) == "ok"
    gql_env.assert_not_called()


# ---------------------------------------------------------------------------
# Token-minting identity endpoints (AWS IAM, Azure Entra)
# ---------------------------------------------------------------------------


def test_identity_network_policy_denial_uses_client_ip():
    from api.utils.identity.common import network_policy_denial

    sa = MagicMock()
    request = MagicMock()
    with patch(
        "api.utils.access.ip.get_client_ip", return_value="192.0.2.10"
    ), patch.object(np, "network_access_denied", return_value=True) as denied, patch.object(
        np, "feature_enabled", return_value=True
    ):
        response = network_policy_denial(request, sa)
    denied.assert_called_once_with(sa.organisation, sa, "192.0.2.10")
    assert response.status_code == 403
    assert np.DENIED_MESSAGE.encode() in response.content


def test_identity_network_policy_allows():
    from api.utils.identity.common import network_policy_denial

    with patch("api.utils.access.ip.get_client_ip", return_value="10.1.2.3"), patch.object(
        np, "network_access_denied", return_value=False
    ):
        assert network_policy_denial(MagicMock(), MagicMock()) is None
