"""Org-level SSO (Entra ID / Okta) is not available in LibreSeal by default."""

from unittest.mock import MagicMock

import pytest
from graphql import GraphQLError

from api.utils.sso import ORG_SSO_PROVIDER_REGISTRY, get_org_provider_meta


@pytest.mark.parametrize("provider_type", sorted(ORG_SSO_PROVIDER_REGISTRY))
def test_org_provider_meta_unavailable(provider_type):
    assert get_org_provider_meta(provider_type) is None


def test_sso_entitlement_refused():
    from backend.graphene.mutations.sso import _check_sso_entitlement

    with pytest.raises(GraphQLError, match="not available in LibreSeal"):
        _check_sso_entitlement(MagicMock())


def test_instance_registry_references_no_enterprise_adapters():
    from api.views import sso

    with open(sso.__file__) as f:
        assert '"ee.' not in f.read()
