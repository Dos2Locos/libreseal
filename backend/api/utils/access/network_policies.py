"""Network access policy evaluation for LibreSeal.

Upstream Phase verifies client IPs against policies with code that is only
available under the Phase Enterprise License, so LibreSeal has no verifier.
Policies can only exist in a database migrated from Phase (creating them is
refused). A control that cannot be enforced must not be silently ignored:
any account with an applicable policy is denied (fail closed).
"""

from api.models import NetworkAccessPolicy
from backend.edition import Feature, feature_enabled

UNENFORCEABLE_MESSAGE = (
    "Access denied: network access policies apply to this account but "
    "LibreSeal cannot enforce them. An administrator must remove the "
    "policies (see `python manage.py libreseal_clear_network_policies`)."
)


def has_applicable_policies(organisation, account):
    """True if the account (org member or service account) has policies of
    its own, or its organisation has global policies."""
    if account is not None and account.network_policies.exists():
        return True
    return NetworkAccessPolicy.objects.filter(
        organisation=organisation, is_global=True
    ).exists()


def network_access_denied(organisation, account):
    """True when access must be denied because applicable policies cannot be
    enforced in this edition."""
    if organisation is None:
        return False
    if feature_enabled(Feature.NETWORK_POLICIES):  # pragma: no cover
        raise NotImplementedError("No network policy verifier is available")
    return has_applicable_policies(organisation, account)
