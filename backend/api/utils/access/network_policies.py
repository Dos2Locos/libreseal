"""Network access policy evaluation for LibreSeal.

Clean-room implementation written from the NetworkAccessPolicy data model
(``allowed_ips``: comma-separated IP addresses or CIDR ranges) and the
LibreSeal specification only. No upstream Enterprise-licensed code was
consulted.

Semantics:
- Policies apply to an account (organisation member or service account) when
  the account has policies of its own or its organisation has global policies.
- When policies apply, access is allowed only if the client IP is contained in
  at least one entry of at least one applicable policy.
- Entries that are not valid IPs/CIDRs never grant access; a missing or
  unparseable client IP is denied (fail closed).
- If the edition disables the feature, any applicable policy denies access.
"""

from ipaddress import ip_address, ip_network

from api.models import NetworkAccessPolicy
from backend.edition import Feature, feature_enabled

DENIED_MESSAGE = (
    "Access denied: a network access policy restricts access from your IP address."
)

UNENFORCEABLE_MESSAGE = (
    "Access denied: network access policies apply to this account but "
    "LibreSeal cannot enforce them. An administrator must remove the "
    "policies (see `python manage.py libreseal_clear_network_policies`)."
)


def _entries(allowed_ips):
    return [e.strip() for e in (allowed_ips or "").split(",") if e.strip()]


def parse_network(entry):
    """Return an ip_network for an IP or CIDR string, or None if invalid."""
    try:
        return ip_network(entry, strict=False)
    except ValueError:
        return None


def invalid_entries(allowed_ips):
    """Entries of an ``allowed_ips`` string that are not valid IPs/CIDRs."""
    return [e for e in _entries(allowed_ips) if parse_network(e) is None]


def validate_allowed_ips(allowed_ips):
    """Raise ValueError unless ``allowed_ips`` holds at least one entry and all
    entries are valid IP addresses or CIDR ranges."""
    entries = _entries(allowed_ips)
    if not entries:
        raise ValueError("At least one IP address or CIDR range is required.")
    bad = invalid_entries(allowed_ips)
    if bad:
        raise ValueError(
            "Invalid IP address or CIDR range: " + ", ".join(sorted(set(bad)))
        )


def _normalise_ip(ip):
    try:
        addr = ip_address((ip or "").strip())
    except ValueError:
        return None
    mapped = getattr(addr, "ipv4_mapped", None)
    return mapped or addr


def ip_matches(ip, allowed_ips):
    """True if ``ip`` is contained in any valid entry of ``allowed_ips``."""
    addr = _normalise_ip(ip)
    if addr is None:
        return False
    for entry in _entries(allowed_ips):
        network = parse_network(entry)
        if network is not None and network.version == addr.version and addr in network:
            return True
    return False


def applicable_policies(organisation, account):
    """Policies of the account plus the organisation's global policies."""
    policies = list(account.network_policies.all()) if account is not None else []
    policies += list(
        NetworkAccessPolicy.objects.filter(organisation=organisation, is_global=True)
    )
    seen, unique = set(), []
    for policy in policies:
        if policy.id not in seen:
            seen.add(policy.id)
            unique.append(policy)
    return unique


def has_applicable_policies(organisation, account):
    """True if the account has policies of its own, or its organisation has
    global policies."""
    if account is not None and account.network_policies.exists():
        return True
    return NetworkAccessPolicy.objects.filter(
        organisation=organisation, is_global=True
    ).exists()


def network_access_denied(organisation, account, ip):
    """True when applicable network access policies deny ``ip``."""
    if organisation is None:
        return False
    if not feature_enabled(Feature.NETWORK_POLICIES):
        return has_applicable_policies(organisation, account)
    policies = applicable_policies(organisation, account)
    if not policies:
        return False
    return not any(ip_matches(ip, p.allowed_ips) for p in policies)


def denial_message():
    if feature_enabled(Feature.NETWORK_POLICIES):
        return DENIED_MESSAGE
    return UNENFORCEABLE_MESSAGE
