"""Unit tests for backend.quotas helpers in LibreSeal (no plan quotas)."""

from unittest.mock import MagicMock

import pytest

from backend import quotas


def _org(plan):
    org = MagicMock()
    org.plan = plan
    return org


@pytest.mark.parametrize("plan", ["FR", "PR", "EN"])
def test_no_quotas_regardless_of_stored_plan(plan):
    org = _org(plan)
    app = MagicMock(organisation=org)

    assert quotas.can_add_app(org) is True
    assert quotas.can_add_account(org, count=500) is True
    assert quotas.can_add_account(org, count=500, account_type="service_account")
    assert quotas.can_add_environment(app) is True
    assert quotas.can_add_environments(org, 100) is True


@pytest.mark.parametrize("plan", ["FR", "PR", "EN"])
def test_core_features_available_regardless_of_stored_plan(plan):
    org = _org(plan)
    assert quotas.can_use_custom_envs(org) is True
    assert quotas.can_use_teams(org) is True


@pytest.mark.parametrize("plan", ["FR", "PR", "EN"])
def test_enterprise_only_features_unavailable_even_on_en_plan(plan):
    """A stored Enterprise plan must not unlock features LibreSeal lacks."""
    org = _org(plan)
    assert quotas.can_use_scim(org) is False
    assert quotas.can_use_log_streams(org) is False
    assert quotas.can_use_rotating_secrets(org) is False


def test_reported_limits_are_unlimited():
    assert quotas.LIBRESEAL_LIMITS["max_users"] is None
    assert quotas.LIBRESEAL_LIMITS["max_apps"] is None
    assert quotas.LIBRESEAL_LIMITS["max_envs_per_app"] is None
