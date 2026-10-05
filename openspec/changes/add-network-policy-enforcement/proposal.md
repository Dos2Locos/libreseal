# Proposal

## Why

`establish-libreseal` had to make network access policies fail closed because the upstream IP verifier lives in Phase's Enterprise-licensed `ee/` code. Policies are an important control for homelabs exposing LibreSeal beyond the LAN (e.g. allow CI runners or a VPN range only), so LibreSeal needs its own verifier.

## What Changes

- Clean-room implementation of IP/CIDR allow-list evaluation for network access policies (IPv4 and IPv6), written from the data model and documented behaviour only, without consulting any `ee/` source. The PR must state this.
- Enable `Feature.NETWORK_POLICIES` in the edition registry: creating, editing and assigning policies works again in UI and GraphQL.
- Enforcement in both REST and GraphQL paths: an account with applicable policies (own or organisation-global) is allowed only from a matching client IP; malformed policy entries deny (fail closed).
- Explicit trusted-proxy handling for client IP resolution so `X-Forwarded-For` cannot be spoofed when LibreSeal is reachable without the bundled nginx.
- `libreseal_clear_network_policies` remains as a break-glass tool; README documents lock-out recovery.

Depends on: `establish-libreseal` being archived (it creates the `feature-availability` spec this change modifies).

Out of scope: geo-IP, per-environment policies, rate limiting. Repos touched: `libreseal` only.

No `ee/` code is involved; the existing upstream `ee/access/utils/network.py` must not be read or referenced.

## Capabilities

### New Capabilities
_(none)_

### Modified Capabilities
- `feature-availability`: network policies change from "fail closed / unavailable" to "enforced allow-lists".

## Impact

`backend/api/utils/access/network_policies.py`, both access middlewares, `backend/backend/edition.py`, `api/utils/access/ip.py` (trusted proxies setting), network policy UI components (remove the unavailable badge), tests, README.
