from ipaddress import ip_address, ip_network

from django.conf import settings

# Networks whose connections may set X-Real-IP / X-Forwarded-For. Defaults to
# loopback and private ranges (the Docker Compose network where the bundled
# nginx runs). Override with the TRUSTED_PROXY_CIDRS setting.
DEFAULT_TRUSTED_PROXY_CIDRS = (
    "127.0.0.0/8",
    "::1/128",
    "10.0.0.0/8",
    "172.16.0.0/12",
    "192.168.0.0/16",
    "fc00::/7",
)


def _trusted_proxy_networks():
    cidrs = getattr(settings, "TRUSTED_PROXY_CIDRS", None) or DEFAULT_TRUSTED_PROXY_CIDRS
    networks = []
    for cidr in cidrs:
        try:
            networks.append(ip_network(cidr.strip(), strict=False))
        except ValueError:
            continue
    return networks


def is_trusted_proxy(ip):
    try:
        addr = ip_address(ip)
    except (TypeError, ValueError):
        return False
    addr = getattr(addr, "ipv4_mapped", None) or addr
    return any(addr.version == n.version and addr in n for n in _trusted_proxy_networks())


def _validate_ip(raw_ip):
    """Validate and return a cleaned IP string, or None if invalid."""
    raw_ip = (raw_ip or "").strip()
    if not raw_ip:
        return None
    try:
        ip_address(raw_ip)
        return raw_ip
    except ValueError:
        return None


def get_client_ip(request):
    """
    Get the client IP address as a single string.

    Forwarded headers (X-Real-IP, then the first X-Forwarded-For entry) are
    honoured only when the direct peer (REMOTE_ADDR) is a trusted proxy;
    otherwise they could be spoofed by any client that reaches the backend
    directly. Falls back to REMOTE_ADDR.

    Args:
        request: Django request object

    Returns:
        str | None: The client IP address (IPv4 or IPv6)
    """
    remote_addr = _validate_ip(request.META.get("REMOTE_ADDR"))

    if remote_addr and is_trusted_proxy(remote_addr):
        # Prefer X-Real-IP (set by nginx)
        ip = _validate_ip(request.META.get("HTTP_X_REAL_IP"))
        if ip:
            return ip

        # Fall back to X-Forwarded-For (first entry is the original client)
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if x_forwarded_for:
            ip = _validate_ip(x_forwarded_for.split(",")[0])
            if ip:
                return ip

    return remote_addr
