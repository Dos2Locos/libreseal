# Design

## Context

See `proposal.md`. Current state: `api/utils/access/network_policies.py` denies any account with applicable policies; `edition.Feature.NETWORK_POLICIES` is disabled; `api/utils/access/ip.get_client_ip` trusts `X-Real-IP`/`X-Forwarded-For` unconditionally (safe only behind the bundled nginx, which overwrites `X-Real-IP`).

## Goals / Non-Goals

**Goals:** clean-room verifier; same data model (`NetworkAccessPolicy.allowed_ips`, comma-separated IPs/CIDRs); no schema migration.
**Non-Goals:** reusing or porting upstream code; changing GraphQL/REST contracts.

## Decisions

- **Clean-room process**: the implementer works only from `api/models.py`, the UI form, public documentation of CIDR semantics and this spec. The PR description includes a statement that no `ee/` file was opened; reviewers check `git log -p` touches no `ee/` path.
- **Evaluation** with Python's `ipaddress` (`ip_address(ip) in ip_network(entry, strict=False)`); entries trimmed; IPv4-mapped IPv6 normalised; invalid entries ignored for matching and rejected at write time (validation added to the create/update mutations).
- **Trusted proxies**: new `TRUSTED_PROXY_CIDRS` setting (default: the Compose network and loopback). Forwarded headers are honoured only when `REMOTE_ADDR` is in that set.
- **Middleware**: keep `network_access_denied(org, account)` as the single entry point; it now returns `not allowed(ip, policies)` when policies apply.

## Risks / Trade-offs

- [Admins lock themselves out] → break-glass command stays; README documents it; UI warns when the admin's current IP is not covered (existing `isClientIpAllowed` helper).
- [Wrong client IP behind other proxies] → the bundled nginx accepts `NGINX_REAL_IP_FROM` / `NGINX_REAL_IP_HEADER` (realip module, `real_ip_recursive on`, values validated by `nginx/real-ip.sh` so a bad value stops nginx instead of trusting everyone). nginx overwrites `X-Real-IP` and `X-Forwarded-For` with the resolved address, so the backend never sees client-supplied chains.

## Migration Plan

No data migration. Deployments that relied on fail-closed behaviour start enforcing allow-lists instead; release notes call this out.
