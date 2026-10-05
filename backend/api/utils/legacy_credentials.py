"""Records migrated from Phase that hold live provider credentials.

Dynamic secrets and secret rotation are not available in LibreSeal, so
their live credentials (active leases, active rotating credentials) cannot
be revoked. Deleting them, directly or through a cascade from their app,
environment or folder, is refused (``FeatureUnavailable``); callers turn
that into this message and roll back any side effects.
"""

REMOVE_COMMAND = "python manage.py libreseal_remove_legacy_credentials"


def cascade_blocked_message(resource):
    return (
        f"This {resource} contains dynamic or rotating secrets with live "
        "provider credentials migrated from Phase, which LibreSeal cannot "
        "revoke. Revoke them at the provider, then remove them with "
        f"`{REMOVE_COMMAND}` before deleting the {resource}."
    )
