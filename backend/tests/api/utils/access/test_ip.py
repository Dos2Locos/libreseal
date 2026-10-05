import pytest
from unittest.mock import MagicMock
from api.utils.access.ip import get_client_ip, _validate_ip


class TestValidateIp:
    @pytest.mark.parametrize(
        "raw, expected",
        [
            ("1.2.3.4", "1.2.3.4"),
            ("  1.2.3.4  ", "1.2.3.4"),
            ("::1", "::1"),
            ("2001:db8::1", "2001:db8::1"),
            ("", None),
            ("   ", None),
            (None, None),
            ("not-an-ip", None),
            ("999.999.999.999", None),
            ("1.2.3.4/24", None),
        ],
    )
    def test_validate_ip(self, raw, expected):
        assert _validate_ip(raw) == expected


def _make_request(**meta):
    req = MagicMock()
    req.META = meta
    return req


class TestGetClientIp:
    def test_x_real_ip_preferred(self):
        req = _make_request(
            HTTP_X_REAL_IP="10.0.0.1",
            HTTP_X_FORWARDED_FOR="10.0.0.2, 10.0.0.3",
            REMOTE_ADDR="10.0.0.4",
        )
        assert get_client_ip(req) == "10.0.0.1"

    def test_falls_back_to_x_forwarded_for(self):
        req = _make_request(
            HTTP_X_FORWARDED_FOR="203.0.113.50, 70.41.3.18",
            REMOTE_ADDR="127.0.0.1",
        )
        # Right-most untrusted hop: 70.41.3.18 connected to the trusted
        # proxy; 203.0.113.50 is only what that client claimed.
        assert get_client_ip(req) == "70.41.3.18"

    def test_x_forwarded_for_single_entry(self):
        req = _make_request(HTTP_X_FORWARDED_FOR="203.0.113.50", REMOTE_ADDR="172.18.0.5")
        assert get_client_ip(req) == "203.0.113.50"

    def test_falls_back_to_remote_addr(self):
        req = _make_request(REMOTE_ADDR="192.168.1.1")
        assert get_client_ip(req) == "192.168.1.1"

    def test_no_headers_returns_none(self):
        req = _make_request()
        assert get_client_ip(req) is None

    def test_invalid_x_real_ip_falls_through(self):
        req = _make_request(
            HTTP_X_REAL_IP="garbage",
            REMOTE_ADDR="10.0.0.1",
        )
        assert get_client_ip(req) == "10.0.0.1"

    def test_invalid_x_forwarded_for_falls_through(self):
        req = _make_request(
            HTTP_X_FORWARDED_FOR="garbage, 10.0.0.2",
            REMOTE_ADDR="10.0.0.1",
        )
        # 10.0.0.2 is a trusted hop and the next entry is malformed, so
        # the chain is unusable and REMOTE_ADDR is used
        assert get_client_ip(req) == "10.0.0.1"

    def test_ipv6_x_real_ip(self):
        req = _make_request(HTTP_X_REAL_IP="2001:db8::1", REMOTE_ADDR="fd00::5")
        assert get_client_ip(req) == "2001:db8::1"

    def test_empty_x_real_ip_falls_through(self):
        req = _make_request(
            HTTP_X_REAL_IP="",
            REMOTE_ADDR="10.0.0.1",
        )
        assert get_client_ip(req) == "10.0.0.1"

    def test_whitespace_only_x_real_ip_falls_through(self):
        req = _make_request(
            HTTP_X_REAL_IP="   ",
            HTTP_X_FORWARDED_FOR="203.0.113.50",
            REMOTE_ADDR="127.0.0.1",
        )
        assert get_client_ip(req) == "203.0.113.50"


class TestTrustedProxies:
    """Forwarded headers are only honoured from trusted proxies (LibreSeal)."""

    def test_spoofed_headers_from_untrusted_peer_are_ignored(self):
        req = _make_request(
            HTTP_X_REAL_IP="10.1.2.3",
            HTTP_X_FORWARDED_FOR="10.1.2.3",
            REMOTE_ADDR="198.51.100.7",
        )
        assert get_client_ip(req) == "198.51.100.7"

    def test_headers_without_peer_are_ignored(self):
        req = _make_request(HTTP_X_REAL_IP="10.1.2.3")
        assert get_client_ip(req) is None

    def test_custom_trusted_proxy_setting(self, settings):
        settings.TRUSTED_PROXY_CIDRS = ["198.51.100.0/24"]
        req = _make_request(HTTP_X_REAL_IP="203.0.113.9", REMOTE_ADDR="198.51.100.7")
        assert get_client_ip(req) == "203.0.113.9"
        req = _make_request(HTTP_X_REAL_IP="203.0.113.9", REMOTE_ADDR="10.0.0.5")
        assert get_client_ip(req) == "10.0.0.5"

    def test_ipv4_mapped_peer_is_trusted(self):
        req = _make_request(HTTP_X_REAL_IP="203.0.113.9", REMOTE_ADDR="::ffff:172.18.0.2")
        assert get_client_ip(req) == "203.0.113.9"


class TestForwardedForChain:
    """X-Forwarded-For is resolved right to left (LibreSeal)."""

    def test_client_prepended_entry_is_ignored(self):
        # A client sends "X-Forwarded-For: 10.1.2.3"; an appending trusted
        # proxy adds the real address 198.51.100.7.
        req = _make_request(
            HTTP_X_FORWARDED_FOR="10.1.2.3, 198.51.100.7",
            REMOTE_ADDR="172.18.0.5",
        )
        assert get_client_ip(req) == "198.51.100.7"

    def test_trusted_hops_are_skipped(self):
        req = _make_request(
            HTTP_X_FORWARDED_FOR="203.0.113.9, 172.18.0.7, 10.0.0.3",
            REMOTE_ADDR="172.18.0.5",
        )
        assert get_client_ip(req) == "203.0.113.9"

    def test_all_hops_trusted_returns_left_most(self):
        req = _make_request(
            HTTP_X_FORWARDED_FOR="192.168.1.20, 172.18.0.7",
            REMOTE_ADDR="172.18.0.5",
        )
        assert get_client_ip(req) == "192.168.1.20"

    def test_malformed_hop_falls_back_to_peer(self):
        req = _make_request(
            HTTP_X_FORWARDED_FOR="203.0.113.9, garbage",
            REMOTE_ADDR="172.18.0.5",
        )
        assert get_client_ip(req) == "172.18.0.5"

    def test_custom_trusted_proxies_define_hops(self, settings):
        settings.TRUSTED_PROXY_CIDRS = ["198.51.100.0/24"]
        req = _make_request(
            HTTP_X_FORWARDED_FOR="203.0.113.9, 10.0.0.3, 198.51.100.8",
            REMOTE_ADDR="198.51.100.7",
        )
        # 10.0.0.3 is not trusted under this setting, so it is the client.
        assert get_client_ip(req) == "10.0.0.3"
