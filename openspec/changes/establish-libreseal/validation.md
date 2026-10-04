# Validación — establish-libreseal

Registro de comprobaciones ejecutadas. Solo se anota lo que se ha ejecutado de verdad; los secretos usados son sintéticos.

Entorno: macOS 26 (arm64), Docker 29.7.2 / Compose v5.5.1, Python 3.12.11 (uv venv), Node 26.10.0, Yarn 1.22.22, Go 1.26.3.

## 1. Línea base upstream (phasehq/console@cbe10457, antes de cambios)

| Comprobación | Comando | Resultado |
|---|---|---|
| Tests backend (incluye `tests/ee`) | `pytest tests/ -q` (backend, venv 3.12) | 2893 passed (de ellos 386 en `tests/ee`) |
| Tipos frontend | `npx tsc --noEmit -p .` | exit 0 |
| Tests frontend | `CI=1 yarn test` (jest) | 22 suites, 459 tests passed |

## 2. Backend sin `ee/`

| Comprobación | Comando | Resultado |
|---|---|---|
| Django system check sin `backend/ee` | `python manage.py check` | "System check identified no issues" |
| Carga del esquema GraphQL sin `ee` | `manage.py shell -c "from backend.schema import schema"` | OK |
| Tests backend | `pytest tests/ -q` | 2490 passed, 0 failed |
| Sin código ee en backend | `git ls-files \| grep -E '(^\|/)ee/' \| grep ^backend` | vacío |
| Nombres indefinidos en ficheros tocados | `ruff check --select F821` | sin errores |

Diferencia de recuento respecto a la línea base: −386 tests de `tests/ee` (código Enterprise retirado), −1 módulo `test_stripe_checkout_details.py`, tests de SSO por organización que importaban adaptadores `ee` (Entra ID: `EntraIdTenantPinningTest`, `EntraIdTenantResolutionTest`, `CloudModeGuardRemovalTest`), tests de Stripe en transferencia de propiedad (`TestUpdateStripeCustomerEmail`, 2 tests de email de facturación), tests de revocación de leases (`TestRevokeLeaseNow`, sustituidos por uno de fallo cerrado), test de "self-hosted skips stripe", parámetros de `DynamicSecrets*View` en `test_fail_closed_rbac.py`; tests SCIM de borrado de miembro reescritos al camino normal. Nuevos: `test_edition.py`, `test_libreseal_feature_gates.py`, `test_libreseal_org_sso_unavailable.py`, `test_quotas.py` y `graphene/queries/test_quotas.py` reescritos.

## 3. Instancia local (clon limpio, `libreseal-init.sh --https-port 8443 --http-port 8080`, `docker compose up -d --build`)

| Comprobación | Resultado |
|---|---|
| 7.1 Instalación limpia | Todos los servicios `running`, backend/postgres `healthy`, migraciones exit 0; `/login` 200; `/service/health/` → `{"status":"alive","version":"v0.1.0"}`; `/app/ee` ausente en la imagen backend |
| Marca (3.1/3.2) | Captura de `/login`: logotipo LibreSeal, título "Log in \| LibreSeal", aviso de fork independiente |
| 7.2 CRUD UI (Playwright) | Registro + onboarding (kit de recuperación descargado), app `demo` con Development/Staging/Production; crear/editar/borrar `LS_TEST_KEY` persiste tras recargar; el valor en claro no aparece en ninguna petición (E2EE) |
| 7.3 API + cuentas de servicio | `agent-demo` (rol Service, solo Development): POST 200, GET 200 con valor correcto, Production → **401** "Service account cannot access this environment"; `agent-readonly` (rol personalizado): GET 200, POST 403 y no se crea; token eliminado → 401. La API REST requiere SSE activado en la app (comportamiento upstream) |
| 7.4 Sin cuotas | Rol personalizado, equipo, 4.º entorno personalizado (`qa`), 6 cuentas de servicio y 6 invitaciones en org con plan almacenado `FR`: todo OK. `libresealFeatures` devuelve las 4 funciones núcleo. Log streams, dynamic secrets, SCIM y OIDC muestran "not available in LibreSeal"; `/v1/secrets/dynamic/`, webhook Stripe y SCIM → 404 |

Nota: la denegación por entorno devuelve 401 (contrato upstream), no 403; el escenario de la spec debe aceptar 401/403.

## Pendiente

7.5 persistencia, 7.6 copia/restauración, 7.7 CLI contra la instancia (plan: ejecutar el binario Linux en un contenedor con `--network container:libreseal-nginx` para no tocar el llavero del host), 7.8 captura de conexiones salientes, 7.9 skills/agent-demo, 7.10 validate + matriz, grupo 8 (README, PRs, siguiente cambio).
