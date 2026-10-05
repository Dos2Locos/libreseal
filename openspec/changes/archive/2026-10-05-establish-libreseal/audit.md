# Auditoría del ecosistema Phase (base: phasehq/console@cbe10457 v2.77.2, phasehq/cli main, phasehq/ai main — 2026-10-04)

Leyenda de decisión: **CONSERVAR** · **ELIMINAR** · **SIMPLIFICAR** · **POSPONER** (cambio separado) · **CARENCIA** (solo existe bajo licencia incompatible).

## 1. Upstreams y licencias

| Repo upstream | Licencia | Fork LibreSeal | Motivo del fork |
|---|---|---|---|
| `phasehq/console` | MIT (Phi Security Inc.) salvo `backend/ee/` y `frontend/ee/` → *Phase Console Enterprise License* | `Dos2Locos/libreseal` | Servidor |
| `phasehq/cli` (Go) | GPL-3.0 | `Dos2Locos/libreseal-cli` | Host por defecto Phase Cloud, `update` desde `pkg.phase.dev`, nombre `phase`, skill embebido |
| `phasehq/ai` | MIT | `Dos2Locos/libreseal-skills` | Skills de despliegue usan imágenes `phasehq/*` y docs de phase.dev |
| `phasehq/golang-sdk` v2.4.1 | MIT | — (dependencia sin cambios) | El CLI lo usa vía `go.mod`; acepta host configurable |
| `phasehq/node-sdk`, `python-sdk`, `client-js-sdk`, `terraform-provider-phase`, `kubernetes-secrets-operator` (GPL-3.0) | MIT / GPL | — | Fuera del alcance inicial; compatibles mientras no cambie el contrato de API |

Condiciones de `ee/LICENSE`: uso en producción solo con suscripción Phase; modificaciones pertenecen a Phase; prohibido copiar, publicar, distribuir o sublicenciar salvo desarrollo/pruebas. **Consecuencia:** LibreSeal no distribuye `ee/` en su árbol ni en sus imágenes. El historial heredado del fork de GitHub contiene `ee/` (lo permite el mecanismo de fork de GitHub sobre un repo público); el árbol de LibreSeal lo elimina a partir de este cambio.

## 2. Acoplamiento del núcleo MIT con `ee/`

Backend (importaciones desde código MIT):
- Arranque: `backend/backend/settings.py:6` (`check_license`), `:483` (`ee.settings.STRIPE`); `api/config.py:22-35` (licencias y *sweeper* de log streams); `api/management/commands/rqworker.py:106`.
- Esquema GraphQL: `backend/backend/schema.py:13-206` (dynamic secrets, rotation, log streams, billing Stripe, SCIM); `backend/backend/graphene/types.py:8-9`.
- REST: `backend/backend/urls.py:105` (`v1/secrets/dynamic/`), `:142` (SCIM), `:156` (webhook Stripe); `api/views/secrets.py:38-44`.
- Modelos/señales: `api/models.py:937,1125,1829`; `api/signals.py:36`.
- Facturación: `update_stripe_subscription_seats` en `graphene/mutations/{service_accounts,account,organisation}.py`, `api/views/{service_accounts,members}.py`; `create_stripe_customer`/`activate_license` en `graphene/mutations/organisation.py:100-105`.
- Seguridad: `is_ip_allowed` en `backend/graphene/middleware.py:431` y `api/utils/access/middleware.py:40`; SCIM `deactivate_scim_user` en `graphene/mutations/organisation.py:665` y `api/views/members.py:413`.
- SSO empresarial (adaptadores en `ee/`): `api/views/sso.py:205-269`, `api/utils/sso.py:37,59` (Entra ID, Okta, Google OIDC, JumpCloud, GitHub Enterprise).

Frontend: `frontend/ee/billing/*` (Stripe, License, PostCheckout), `ee/components/secrets/{dynamic,rotation}/*`, `ee/components/logstreams/*`, `ee/utils/dynamicSecrets.ts`; importados por `app/[team]/apps/[app]/environments/[environment]/[[...path]]/page.tsx`, `_hooks/useAppSecrets.ts`, `integrations/{dynamic-secrets,log-streams}/page.tsx`, `app/onboard/page.tsx`, `components/settings/organisation/PlanInfo.tsx`.

Tests MIT que importan `ee/`: `backend/tests/test_quotas.py`, `test_org_sso.py`, `test_sso_providers.py`, `api/mutations/test_{delete_account,delete_organisation_member,transfer_ownership}.py`, `graphene/queries/test_{stripe_checkout_details,quotas}.py`, `api/views/test_fail_closed_rbac.py`.

## 3. Planes, cuotas y entitlements (restricciones comerciales)

| Símbolo | Restricción | Decisión |
|---|---|---|
| `backend/backend/quotas.py` `PLAN_CONFIG` | Free: 3 entornos/app; Pro: 10 | **ELIMINAR** límite (núcleo ilimitado) |
| `can_add_app`, `can_add_account`, `can_add_environment(s)` | apps/asientos/entornos por plan o licencia | **SIMPLIFICAR**: siempre permitido en LibreSeal |
| `can_use_custom_envs` (`plan != "FR"`) | entornos personalizados | **ELIMINAR** restricción |
| `can_use_teams` | equipos solo Pro/Enterprise | **ELIMINAR** restricción (implementación MIT) |
| `api/views/roles.py:153,303`, `graphene/mutations/access.py:69,146` | roles personalizados solo de pago | **ELIMINAR** restricción (RBAC MIT) |
| `can_use_scim`, `can_use_log_streams`, `can_use_rotating_secrets` | plan Enterprise/Pro | **CARENCIA**: implementación en `ee/` → *no disponible* |
| `backend/graphene/mutations/sso.py:_check_sso_entitlement` + `ActivatedPhaseLicense` | SSO OIDC empresarial | **CARENCIA** (adaptadores en `ee/`) |
| `Organisation.plan`, `pricing_version`, `ActivatedPhaseLicense`, `PlanTypeEnum` | campos de BD y GraphQL | **CONSERVAR** sin uso para *gating* (compatibilidad de esquema y migraciones) |
| `backend/graphene/queries/quotas.py` | expone plan y asientos | **SIMPLIFICAR**: sin límites |
| UI: `UpsellDialog`, `UpgradeRequestForm` (POST a `NEXT_PUBLIC_SLACK_NOTIF_URL`), `PlanLabel`, `PlanInfo` y ~20 comprobaciones `organisation.plan` | venta / upgrade | **ELIMINAR** y sustituir por disponibilidad de funciones LibreSeal |

## 4. Facturación y servicios comerciales

Stripe (`ee/billing/*`, webhook en `urls.py:156`, `@stripe/*` en `frontend/package.json`, `NEXT_PUBLIC_STRIPE_PUBLIC_KEY`), notificador Slack de altas (`backend/backend/api/notifier.py`, usado en `api/signals.py:26` solo si `APP_HOST=cloud`), Cloudflare KV (`backend/backend/api/kv.py`, solo nube). **ELIMINAR** Stripe y el formulario de upgrade; **CONSERVAR inertes** (detrás de `APP_HOST=cloud`) KV/Slack en este cambio, **POSPONER** su retirada a un cambio de limpieza del modo nube.

## 5. Telemetría y conexiones salientes (verificadas)

| Origen | Destino | Condición actual | Decisión |
|---|---|---|---|
| `frontend/utils/posthog.ts`, `app/providers.tsx`, `contexts/organisationContext.tsx:46` (`identify`), `apollo/client.ts:58` | PostHog (analítica + **grabación de sesión**) | solo si `NEXT_PUBLIC_POSTHOG_KEY/HOST` configurados | **ELIMINAR** |
| `frontend/components/common/StatusIndicator.tsx:14` en `layout/Navbar.tsx:114` | `phase.statuspage.io` | **siempre** en cada navegador autenticado | **ELIMINAR** del navbar |
| `frontend/components/ReleaseInfo.tsx:25` (página de ajustes) | `api.github.com/repos/phasehq/console` | siempre al abrir ajustes | **SIMPLIFICAR**: versión local, sin consulta remota |
| Enlaces a `docs.phase.dev`, `console.phase.dev`, `slack.phase.dev` | navegación del usuario | — | **SIMPLIFICAR**: apuntar a docs LibreSeal |
| `backend/Dockerfile` | `truststore.pki.rds.amazonaws.com` (CA de RDS en build) | build | **CONSERVAR** (solo build; POSPONER) |
| Next.js | telemetría de Next | ya desactivada (`NEXT_TELEMETRY_DISABLED=1`) | CONSERVAR |
| CLI `cmd/update.go` | descarga y ejecuta `https://pkg.phase.dev/install.sh` | comando `update` (Linux) | **ELIMINAR/REEMPLAZAR** |
| CLI `pkg/config/config.go:11` | `PhaseCloudAPIHost = https://console.phase.dev` como host por defecto | `auth` sin host | **ELIMINAR** default; host obligatorio |

## 6. Seguridad (no comercial): conservar

E2EE cliente (libsodium, claves de entorno envueltas), RBAC (`api/utils/access/permissions.py`, roles por defecto), tokens de servicio y cuentas de servicio, auditoría (`SecretEvent`), recuperación por *recovery phrase* (frontend `utils/crypto`), CSRF, `fail_closed_rbac`. **Políticas de red**: los modelos y la UI son MIT pero la comprobación `is_ip_allowed` está en `ee/` y upstream solo la aplica fuera del plan Free. LibreSeal: **CARENCIA** → bloquear la creación y *fallar cerrado* si existen políticas heredadas; implementación propia en cambio separado (sala limpia).

## 7. Contratos de API, tokens y CLI

REST `/service/public/v1/secrets/` (cabecera `Authorization: Bearer ServiceAccount <token>` / `User <pat>`), GraphQL `/service/graphql`, formatos de token `pss_service:v2:...` / `pss_user:v1:...`: **CONSERVAR sin cambios**. El CLI usa `phasehq/golang-sdk` y `PHASE_HOST`, `PHASE_SERVICE_TOKEN`, `PHASE_VERIFY_SSL`; configuración en `~/.phase/` y `.phase.json`. Los comandos `dynamic-secrets *` dependen de `v1/secrets/dynamic/` (ee) → devolverán error controlado.

## 8. Skills

- `phasehq/ai`: skills de despliegue (`docker-compose`, `k8s`, `eks`, `aks`), imágenes `phasehq/frontend|backend`, Helm chart de Phase, docs phase.dev. Sin scripts ejecutables. Adaptar `docker-compose`; **POSPONER** k8s/eks/aks.
- Skill de uso embebido en el CLI (`src/pkg/ai/PHASE.md`, GPL-3.0) instalado por `phase ai enable`; bloquea `printenv`/`env` dentro de `phase run` y `phase shell` en modo agente. Adaptar a `libreseal`.

## 9. Requisitos para operar sin cuenta comercial

Construir imágenes desde el código fuente (el `docker-compose.yml` actual usa `phasehq/*:latest` de Docker Hub, que incluyen `ee/`), generar secretos aleatorios en la instalación (el `.env.example` trae `SECRET_KEY`/`SERVER_SECRET` fijos), no definir `PHASE_LICENSE_OFFLINE`, `APP_HOST=self`, y CLI apuntando al host propio.
