import pytest

from backend.edition import (
    Feature,
    FeatureUnavailable,
    enabled_features,
    feature_enabled,
)


@pytest.mark.parametrize(
    "feature",
    [
        Feature.CUSTOM_ROLES,
        Feature.TEAMS,
        Feature.CUSTOM_ENVIRONMENTS,
        Feature.SERVICE_ACCOUNTS,
    ],
)
def test_core_features_enabled(feature):
    assert feature_enabled(feature)
    assert feature_enabled(feature.value)


@pytest.mark.parametrize(
    "feature",
    [
        Feature.DYNAMIC_SECRETS,
        Feature.SECRET_ROTATION,
        Feature.LOG_STREAMS,
        Feature.SCIM,
        Feature.ENTERPRISE_SSO,
        Feature.NETWORK_POLICIES,
        Feature.BILLING,
        Feature.LICENSING,
    ],
)
def test_enterprise_only_features_unavailable(feature):
    assert not feature_enabled(feature)


def test_unknown_feature_rejected():
    with pytest.raises(ValueError):
        feature_enabled("does_not_exist")


def test_enabled_features_lists_core_only():
    assert enabled_features() == [
        "custom_environments",
        "custom_roles",
        "service_accounts",
        "teams",
    ]


def test_feature_unavailable_message():
    err = FeatureUnavailable(Feature.LOG_STREAMS)
    assert "not available in LibreSeal" in str(err)
