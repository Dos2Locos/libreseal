"""Resource limits and feature checks.

LibreSeal has no commercial plans: there are no app, environment, seat or
service account quotas. These helpers keep their upstream signatures so call
sites do not change, but they only consult the LibreSeal edition registry
(``backend.edition``). Access is still governed by RBAC at each call site.
"""

from backend.edition import Feature, feature_enabled


# Limits reported to clients through the organisationPlan query. ``None`` means
# unlimited. The upstream per-plan table is intentionally not reproduced.
LIBRESEAL_LIMITS = {
    "name": "LibreSeal",
    "max_users": None,
    "max_apps": None,
    "max_envs_per_app": None,
}


def can_add_app(organisation):
    """Apps are unlimited in LibreSeal."""
    return True


def can_add_account(organisation, count=1, account_type="user"):
    """Human and service accounts are unlimited in LibreSeal."""
    return True


def can_add_environment(app):
    """Environments per app are unlimited in LibreSeal."""
    return True


def can_add_environments(organisation, count):
    """Environments for a new app are unlimited in LibreSeal."""
    return True


def can_use_custom_envs(organisation):
    return feature_enabled(Feature.CUSTOM_ENVIRONMENTS)


def can_use_teams(organisation):
    return feature_enabled(Feature.TEAMS)


def can_use_scim(organisation):
    return feature_enabled(Feature.SCIM)


def can_use_log_streams(organisation):
    return feature_enabled(Feature.LOG_STREAMS)


def can_use_rotating_secrets(organisation):
    return feature_enabled(Feature.SECRET_ROTATION)
