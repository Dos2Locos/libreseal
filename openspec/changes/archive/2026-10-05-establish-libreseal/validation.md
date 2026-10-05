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

| 7.5 Persistencia | `docker compose down && docker compose up -d`: `LS_TEST_KEY` legible por API con el mismo valor |
| 7.6 Copia/restauración | `libreseal-backup.sh` (dump 381 KB, modo 600, verificado con `pg_restore --list`) → `docker compose down -v` (tras el borrado el token devuelve 401) → `up` → `libreseal-restore.sh --yes <dump>` → secreto legible con su valor original |
| Recuperación de cuenta | Frase de 24 palabras del kit PDF en `/homelab/recovery`: acceso restaurado; con el orden alterado se rechaza |
| 7.7 CLI | Binario Linux en contenedor con `--network container:libreseal-nginx` (sin llavero del host). `libreseal-cli/scripts/e2e/cli-e2e.sh`: **29/29** — auth `--mode token` (expect), whoami, apps list, init, create sealed/secret/config, list/get/update/delete, import/export, `run` con MATCH sin el valor en la salida, `run 'true'`, dynamic-secrets "not available on this server", `update` sin dominios de Phase, alias `PHASE_*`, error sin host, solo-lectura deniega escritura y Production, `ai enable` instala el skill, sealed redactado y `printenv`/`shell` bloqueados en modo agente |
| 7.8 Conexiones salientes | Navegador: 1155 + 889 peticiones, todas a `https://localhost:8443`. tcpdump en los namespaces de backend, worker, frontend y nginx (filtro `not (src net S and dst net S)` + DNS; control positivo hacia 1.1.1.1 capturado) durante UI CRUD, equipos y e2e del CLI: sin tráfico externo; todas las respuestas DNS resuelven a IP internas de Compose; nginx solo intercambia tráfico con el host (192.168.65.1, navegador) |
| 7.9 Skills | Comandos de verificación del skill `docker-compose` ejecutados tal cual (servicios `running/healthy`, migraciones exit 0, health y `/login` 200). `libreseal-usage/examples/agent-demo.sh` con `CLAUDECODE=1`: lista apps, comprueba `LS_TEST_KEY` en el proceso sin imprimirlo, Production denegado; `printenv` bloqueado; el valor sintético aparece 0 veces en el log. ShellCheck sin avisos en todos los scripts |
| 7.10 OpenSpec | `openspec validate establish-libreseal --strict`: válido. Specs alineadas con el comportamiento verificado (401/403 en denegación por entorno, instalador del CLI, redacción de sealed en modo agente) |

Combinación verificada: libreseal `7261b032` + libreseal-cli `132264f` (golang-sdk v2.4.1) + libreseal-skills `b88d772`.

## Correcciones tras la revisión de código (después de archivar)

Hallazgos de la revisión del PR #1 y su verificación. Instancia de prueba con el PR #1 integrado en la rama del PR #2; datos de Phase simulados con registros sintéticos.

| Hallazgo | Corrección | Verificación |
|---|---|---|
| Secretos dinámicos omitidos en silencio al pedirlos por REST | 501 explícito si se piden (`dynamic`/`include_dynamic`) y el entorno contiene secretos dinámicos migrados; sin ellos, respuesta normal (la CLI los pide por defecto en `run`/`export`/`shell`/`get`) | CLI `secrets export` con un secreto dinámico migrado → "HTTP 501: The dynamic secrets feature is not available…"; REST sin `dynamic` → 200, con `dynamic=true` → 501; tras retirarlo, la CLI vuelve a funcionar |
| Borrar app/entorno/carpeta con credenciales vivas daba 500 (REST) y, en apps, vaciaba `wrapped_key_share` antes del borrado abortado | Borrados en transacción; el rechazo se convierte en error claro (GraphQL) o 409 (REST); los secretos dinámicos con leases activos quedan protegidos de la cascada como los rotativos | GraphQL como Owner con un secreto rotativo con credencial activa: `deleteEnvironment` y `deleteApp` rechazados con el mensaje; entorno y app siguen existiendo, `wrapped_key_share` intacto, 0 eventos de auditoría nuevos |
| Sin forma de retirar registros heredados | Comando `libreseal_remove_legacy_credentials`: lista; `--yes` borra los que no tienen credenciales vivas; `--yes --credentials-revoked` marca las credenciales como revocadas y borra el resto | Con credencial viva: "Removed 0 records" y aviso; con confirmación: "Removed 1 records", credencial `revoked`, registro borrado |
| Ajustes muertos `PHASE_LICENSE`, `STRIPE` | Eliminados; la consulta `license` devuelve `null` (contrato conservado) | Suite backend |
| "Sin telemetría" sin matices | README matizado (avatares de Google/GitHub/GitLab al iniciar sesión con ellos); origen Gravatar, sin uso, retirado de la CSP | Cabecera CSP servida: `img-src 'self' https://lh3.googleusercontent.com https://avatars.githubusercontent.com https://gitlab.com`; CRUD por UI correcto sin texto en claro |

Tests: suite backend 2509 passed en esta rama (2719 passed, 11 skipped con el PR #2 integrado); nuevos tests de los caminos que fallan cerrado (`tests/test_libreseal_legacy_credentials.py`, borrados REST bloqueados). Se hizo copia de seguridad de la instancia antes de las pruebas de borrado.
