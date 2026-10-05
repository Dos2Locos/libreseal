# LibreSeal

Free, self-hosted secrets management for homelabs and small teams — web UI, REST/GraphQL API, a CLI and agent skills, with end-to-end encryption.

> **LibreSeal is an independent community fork of [Phase Console](https://github.com/phasehq/console).** It is not affiliated with, sponsored by or endorsed by Phase or Phi Security Inc. See [Relationship with Phase](#relationship-with-phase).

## Status

**v0.1.0 — early, homelab-ready.** The core (apps, environments, secrets, service accounts, RBAC, audit logs, syncs, recovery) is inherited from Phase Console v2.77.2 and verified end to end with Docker Compose, the `libreseal` CLI and the agent skills (see [Verified combination](#verified-combination)). There are no pre-built images or packages yet: everything is built from source.

| Area | State |
|------|-------|
| Web UI, secrets CRUD, apps, environments (incl. custom), folders, references, history | ✅ |
| Service accounts, custom roles, teams, least-privilege access, audit logs | ✅ (no plan restrictions) |
| REST API (`/service/public/v1/`) and GraphQL | ✅ (unchanged contracts) |
| End-to-end encryption, account recovery phrase, optional server-side encryption (SSE) | ✅ |
| Third-party syncs (GitHub, GitLab, AWS, GCP, Azure, Vault, Cloudflare, …) | Inherited, not re-verified |
| Sign-in: email/password, Google, GitHub, GitLab, Authentik, Authelia | ✅ password verified; OAuth/OIDC inherited |
| Dynamic secrets, secret rotation, log streams, SCIM, org-level OIDC SSO (Entra ID, Okta, JumpCloud, Google OIDC, GitHub Enterprise) | ❌ Not available (see [Limitations](#compatibility-and-limitations)) |
| Network access policies | ❌ Not enforceable yet — configuration disabled, legacy policies fail closed |
| Kubernetes / Helm | ❌ Not adapted yet |

## Quick start (server)

Requirements: Docker with Compose v2, git, openssl, ~4 GB RAM for the first build.

```sh
git clone https://github.com/Dos2Locos/libreseal.git
cd libreseal
./scripts/libreseal-init.sh                       # writes .env (mode 600) with random secrets
# or: ./scripts/libreseal-init.sh --host secrets.lan --https-port 8443 --http-port 8080
docker compose up -d --build
```

Open `https://<host>[:port]`, create the first account (no SMTP is needed — email verification is skipped when SMTP is not configured), create your organisation and **store the recovery kit offline**.

The bundled nginx uses a self-signed certificate. For LAN use, accept it or mount your own certificate; for public domains see the `docker-compose` skill for Let's Encrypt.

Check health:

```sh
docker compose ps
curl -ks https://localhost/service/health/        # {"status": "alive", "version": "v0.1.0"}
```

Upgrade: `./scripts/libreseal-backup.sh && git pull && docker compose up -d --build` (migrations run automatically).

### Configuration

All settings live in `.env` (template: [`.env.example`](.env.example)). Key variables: `HOST`, `PUBLIC_URL`, `HTTP_PORT`, `HTTPS_PORT`, `ENABLE_PASSWORD_AUTH`, `SSO_PROVIDERS` (`google`, `github`, `gitlab`, `authentik`, `authelia`) and their credentials, optional `SMTP_*`. Never commit `.env`.

## CLI

The CLI lives in [Dos2Locos/libreseal-cli](https://github.com/Dos2Locos/libreseal-cli) (GPL-3.0):

```sh
git clone https://github.com/Dos2Locos/libreseal-cli.git
cd libreseal-cli && ./scripts/install-from-source.sh     # needs Go 1.25+

libreseal auth                                 # asks for your server URL; webauth or --mode token
libreseal apps list
libreseal init --app-id <APP_ID> --env development
libreseal secrets create DB_PASSWORD --random base64url --length 48 --type sealed
libreseal secrets import .env && libreseal secrets export --format json
libreseal run 'npm start'                      # inject secrets into a process
```

`libreseal` has no default host and accepts `LIBRESEAL_HOST` / `LIBRESEAL_SERVICE_TOKEN` (and the `PHASE_*` names as aliases). For a self-signed test instance only: `LIBRESEAL_VERIFY_SSL=False`. `libreseal update` prints update instructions; nothing is downloaded from third parties.

## Agent skills

[Dos2Locos/libreseal-skills](https://github.com/Dos2Locos/libreseal-skills) (MIT):

```sh
npx skills add Dos2Locos/libreseal-skills -s docker-compose     # deploy/backup/upgrade LibreSeal
npx skills add Dos2Locos/libreseal-skills -s libreseal-usage    # use LibreSeal safely from an agent
```

The version-matched CLI guide is embedded in the CLI: a human runs `libreseal ai enable` to install it for Claude Code, Cursor, Copilot, Codex or OpenCode. When an agent is detected the CLI blocks `printenv`/`env`/`export`/`set` inside `libreseal run`, disables `libreseal shell` and redacts sealed values — defence in depth only.

## Permissions for applications and agents

1. Create a **service account** (Access → Service Accounts). Keep the default `Service` role or create a **custom role** (Access → Roles), e.g. read-only (`Secrets: read`, `Environments: read`).
2. Grant it access only to the app and environments it needs (App → Access → Add, or *Add App* on the account).
3. Generate a token (expiry recommended) and hand it to the workload through its environment, never through files in version control:
   ```sh
   export LIBRESEAL_HOST=https://secrets.lan LIBRESEAL_SERVICE_TOKEN='pss_service:v2:…'
   libreseal run './start.sh'
   ```
4. Agents must get their **own** least-privilege service account token — never a personal or admin token.

REST access to decrypted values (`GET /service/public/v1/secrets/?app_id=…&env=…` with `Authorization: Bearer ServiceAccount <token>`) requires enabling **server-side encryption (SSE)** for that app (App → Settings). SSE lets the server read the app's secrets; the CLI and UI work without it (end-to-end encrypted). Out-of-scope requests are denied (401/403).

## Backup and restore

```sh
./scripts/libreseal-backup.sh                 # ./backups/libreseal-<UTC timestamp>.dump (mode 600)
./scripts/libreseal-restore.sh --yes <file>   # replaces ALL data in the running instance
```

A restore needs the dump **and the same `.env`** (`SERVER_SECRET`, `SECRET_KEY`, …). Users still need their password or recovery phrase to decrypt end-to-end encrypted secrets. Keep dumps and `.env` encrypted and in separate places.

## Compatibility and limitations

- **API, token formats and cryptography are unchanged** from Phase Console v2.77.2; existing Phase SDKs and the Phase CLI should keep working (only the `libreseal` CLI is verified).
- **Removed proprietary code.** Upstream ships some features only under the *Phase Console Enterprise License* (`ee/` directories): dynamic secrets, secret rotation, log streams, SCIM, organisation-level OIDC SSO, license activation and billing. LibreSeal does not contain that code; the UI shows these features as *not available* and their APIs return 404 or an explicit error. Re-implementations will only be accepted as clean-room work (written without consulting `ee/` sources), each in its own OpenSpec change.
- **Network access policies** cannot be enforced (the upstream verifier is in `ee/`). Creating/assigning policies is refused; accounts that already have policies (migrated data) are **denied** until an admin removes them with `docker compose exec backend python manage.py libreseal_clear_network_policies --yes`.
- **Migrating from Phase**: restore a Phase `pg_dump` with `libreseal-restore.sh` using the original `SECRET_KEY`/`SERVER_SECRET`. Remove dynamic and rotating secrets in Phase first (revoking their credentials): LibreSeal cannot serve them nor revoke their credentials. Clients that request dynamic secrets get an explicit error in environments that still hold them, and deleting an app, environment or folder that holds live credentials is refused. `docker compose exec backend python manage.py libreseal_remove_legacy_credentials` lists them and, once the credentials are revoked at the provider, removes them (`--yes --credentials-revoked`).
- **No plans or quotas.** The `plan` fields remain in the database/GraphQL schema for compatibility only.
- **No telemetry.** The UI only talks to your server (verified by capturing browser and container traffic with password sign-in); Next.js telemetry is disabled. Exception: users who sign in with Google, GitHub or GitLab have their profile picture loaded from that provider (`lh3.googleusercontent.com`, `avatars.githubusercontent.com`, `gitlab.com`, the only external image origins allowed by the CSP). Third-party syncs and OAuth providers you configure obviously contact their services.
- **Git history** inherited from upstream still contains the `ee/` directories in old commits. Those revisions remain under the Enterprise License and must not be used in production without a Phase subscription.
- Only the Docker Compose deployment is supported; `dev-`, `staging-` and `tailscale-` compose files are upstream leftovers.

### Verified combination

| Component | Version / commit | Verification |
|-----------|------------------|--------------|
| libreseal (server) | `7261b032` (v0.1.0, based on Phase Console v2.77.2) | Clean install, UI CRUD, API + service accounts, RBAC denials, no quotas, persistence, backup/restore, recovery phrase, outbound traffic capture |
| libreseal-cli | `132264f` (golang-sdk v2.4.1) | `scripts/e2e/cli-e2e.sh`: 29/29 |
| libreseal-skills | `b88d772` | `docker-compose` commands, `libreseal-usage/examples/agent-demo.sh` in agent mode |

Details: [`validation.md`](openspec/changes/archive/2026-10-05-establish-libreseal/validation.md) of the archived `establish-libreseal` change.

## Relationship with Phase

LibreSeal started from Phase Console v2.77.2 (MIT, © Phi Security Inc.). We keep the upstream history, copyright notices and [LICENSE](LICENSE); see [NOTICE](NOTICE) for per-component licensing. The LibreSeal name, logo and fork-specific changes are ours; Phase's trademarks belong to their owners. Thanks to the Phase team for building and open-sourcing the platform.

## Contributing (OpenSpec)

LibreSeal uses [OpenSpec](https://github.com/Fission-AI/OpenSpec) for spec-driven changes:

1. Read the project context in [`openspec/config.yaml`](openspec/config.yaml) and current specs in `openspec/specs/`.
2. Propose a bounded change: `openspec new change <name>` (or `/opsx:propose` in a supported agent), then write `proposal.md`, delta specs, `design.md` and `tasks.md`; check with `openspec validate <name> --strict`.
3. Implement task by task (`/opsx:apply`), with tests and executed validation for each task.
4. Open a PR referencing the change; it is archived (`openspec archive <name>`) once its acceptance criteria are verified.

Ground rules: no code derived from `ee/`; never fake plans or licenses; never weaken security controls (fail closed instead); keep API, token and crypto formats compatible unless a change includes a migration plan. Run `scripts/check-libreseal-guard.sh`, backend `pytest` and frontend `yarn test` before opening a PR.

## License

MIT for this repository (see [LICENSE](LICENSE) and [NOTICE](NOTICE)). The CLI is GPL-3.0; the skills are MIT.
