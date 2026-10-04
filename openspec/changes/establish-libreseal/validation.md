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
