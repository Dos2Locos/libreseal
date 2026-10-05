"""LibreSeal edition feature registry.

LibreSeal has no commercial plans, licenses or quotas. Feature availability is
a property of the LibreSeal edition itself, not of an organisation's plan:

- Core features are implemented in MIT-licensed code and are always enabled.
- Unavailable features only exist upstream under the Phase Console Enterprise
  License (``ee/`` directories), which LibreSeal does not ship. They stay
  disabled until a clean-room implementation lands in a separate change.

The ``Organisation.plan`` field is kept for schema compatibility only and must
not be used to gate features. Use ``feature_enabled`` instead.
"""

from enum import Enum


class Feature(str, Enum):
    # Core (MIT) features
    CUSTOM_ROLES = "custom_roles"
    TEAMS = "teams"
    CUSTOM_ENVIRONMENTS = "custom_environments"
    SERVICE_ACCOUNTS = "service_accounts"

    # Upstream Enterprise-only features, not available in LibreSeal
    DYNAMIC_SECRETS = "dynamic_secrets"
    SECRET_ROTATION = "secret_rotation"
    LOG_STREAMS = "log_streams"
    SCIM = "scim"
    ENTERPRISE_SSO = "enterprise_sso"
    NETWORK_POLICIES = "network_policies"
    BILLING = "billing"
    LICENSING = "licensing"


ENABLED_FEATURES = frozenset(
    {
        Feature.CUSTOM_ROLES,
        Feature.TEAMS,
        Feature.CUSTOM_ENVIRONMENTS,
        Feature.SERVICE_ACCOUNTS,
    }
)


class FeatureUnavailable(Exception):
    """Raised when a feature that LibreSeal does not provide is requested."""

    def __init__(self, feature):
        self.feature = Feature(feature)
        super().__init__(unavailable_message(self.feature))


def feature_enabled(feature):
    """Return True if the feature is available in this LibreSeal edition."""
    return Feature(feature) in ENABLED_FEATURES


def enabled_features():
    """Return the sorted names of all enabled features."""
    return sorted(f.value for f in ENABLED_FEATURES)


def unavailable_message(feature):
    name = Feature(feature).value.replace("_", " ")
    return f"The {name} feature is not available in LibreSeal."
