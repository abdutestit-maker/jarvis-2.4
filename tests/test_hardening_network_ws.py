from __future__ import annotations

from core.network_guard import is_ssrf_blocked


def test_network_guard_blocks_loopback_private_link_local_ipv6_and_encoded_hosts(monkeypatch) -> None:
    assert is_ssrf_blocked("http://127.0.0.1/")
    assert is_ssrf_blocked("http://192.168.1.1/")
    assert is_ssrf_blocked("http://169.254.169.254/latest")
    assert is_ssrf_blocked("http://[::1]/")
    assert is_ssrf_blocked("http://localhost/")

    def fake_getaddrinfo(host, *args, **kwargs):
        return [(2, 1, 6, "", ("127.0.0.1", 0))]

    monkeypatch.setattr("core.network_guard.socket.getaddrinfo", fake_getaddrinfo)
    assert is_ssrf_blocked("https://public.example/")

