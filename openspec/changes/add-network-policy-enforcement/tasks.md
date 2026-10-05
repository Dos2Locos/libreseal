# Tasks

## 1. Verifier

- [x] 1.1 Implement IP/CIDR matching in `api/utils/access/network_policies.py` (clean-room, `ipaddress`) with unit tests for IPv4, IPv6, mapped addresses, invalid entries; verify with `pytest`
- [x] 1.2 Add `TRUSTED_PROXY_CIDRS` and make `get_client_ip` honour forwarded headers only from trusted proxies; tests for spoofed headers; verify with `pytest`
- [x] 1.3 Validate `allowed_ips` on create/update mutations; tests; verify with `pytest`
- [x] 1.4 GraphQL enforcement on every organisation-scoped resolver (organisation resolved from any argument, all organisations checked in bulk operations, per-request decision cache) plus a schema-wide test that fails when a root field's organisation cannot be resolved; verify with `pytest` and live (`secrets(envId)` from a denied IP)

## 2. Enablement

- [x] 2.1 Enable `Feature.NETWORK_POLICIES`, update edition/feature-gate tests and remove the "not available" badges in the UI; verify `pytest`, `tsc`, `yarn test`
- [x] 2.2 Document policies, trusted proxies and lock-out recovery in README
- [x] 2.3 Bundled nginx: configurable `NGINX_REAL_IP_FROM`/`NGINX_REAL_IP_HEADER` (realip module, recursive, validated at startup) and overwrite client-supplied forwarding headers; `scripts/tests/test-nginx-real-ip.sh` in CI; verify live behind a trusted outer proxy

## 3. Validation

- [x] 3.1 Local instance: policy allowing the test client → 200; policy excluding it → 403; global policy; spoofed `X-Forwarded-For` ignored; record in `validation.md`
- [x] 3.2 PR statement that no `ee/` source was consulted; `scripts/check-libreseal-guard.sh` passes
