# Proposal

## Why

Phase Console es MIT salvo los directorios `ee/`, cuya licencia prohíbe el uso en producción y la redistribución sin suscripción; además, el núcleo MIT limita funciones propias (entornos, roles, equipos) según planes comerciales, incluye venta/upgrade, telemetría opcional y llamadas a servicios de Phase, y el CLI usa Phase Cloud como host por defecto. LibreSeal necesita una base autoalojada, legalmente redistribuible y sin restricciones artificiales, que conserve UI, API, CLI y skills para agentes. Detalle con referencias en [`audit.md`](./audit.md).

## What Changes

- **Identidad**: marca LibreSeal con recursos visuales propios, aviso de fork independiente sin afiliación con Phase, atribuciones y licencias conservadas.
- **Retirada de `ee/`**: se eliminan `backend/ee/`, `frontend/ee/` y `backend/tests/ee/` del árbol; cada punto de acoplamiento del núcleo MIT pasa a degradarse de forma explícita (función *no disponible*), sin copiar ni reimplementar código `ee/`.
- **Disponibilidad por edición, no por plan**: un registro único de funciones LibreSeal sustituye a `PLAN_CONFIG` y a las comprobaciones `organisation.plan`. Sin límites de apps, entornos, miembros ni cuentas de servicio; roles personalizados, equipos y entornos personalizados habilitados. Los campos `plan`/licencia permanecen en BD y GraphQL solo por compatibilidad. **BREAKING** (comportamiento): las funciones con implementación solo en `ee/` dejan de existir en LibreSeal — dynamic secrets (AWS), rotación, log streams, SCIM, SSO OIDC empresarial (Entra ID, Okta, Google OIDC, JumpCloud, GitHub Enterprise), activación de licencias y facturación.
- **Políticas de red**: sin verificador disponible, la creación queda deshabilitada y las políticas heredadas *fallan cerrado* (deniegan) en lugar de ignorarse.
- **Comercial y telemetría**: se eliminan Stripe, formularios de upgrade/upsell, PostHog (incl. grabación de sesión), el indicador de `phase.statuspage.io` y la consulta a releases de GitHub de Phase; enlaces de documentación hacia LibreSeal.
- **Despliegue**: Docker Compose que construye las imágenes desde el código fuente, script de inicialización que genera secretos aleatorios y procedimiento de copia/restauración de PostgreSQL.
- **CLI** (`Dos2Locos/libreseal-cli`): binario `libreseal`, sin host por defecto de Phase Cloud, sin `update` desde `pkg.phase.dev`, skill embebido adaptado; compatibilidad de flags, variables `PHASE_*` y ficheros `.phase.json`/`~/.phase` conservada.
- **Skills** (`Dos2Locos/libreseal-skills`): skill `docker-compose` adaptado a LibreSeal y skill de uso seguro por agentes con token de cuenta de servicio de mínimo privilegio e inyección de procesos.
- **Documentación**: README con estado real, relación con Phase, instalación, permisos, copia/restauración, compatibilidad y contribución vía OpenSpec.

Fuera de alcance: implementación propia de políticas de red, SSO OIDC, SCIM, rotación, dynamic secrets o log streams (cambios separados); despliegues k8s/EKS/AKS y Helm; publicación de imágenes o binarios en registros; retirada del modo `APP_HOST=cloud` (KV de Cloudflare y notificador Slack quedan inertes); SDKs, operador de Kubernetes y proveedor de Terraform; cambios de cifrado, formatos de token o contratos de API.

Repositorios afectados: `libreseal` (servidor, specs, docs), `libreseal-cli`, `libreseal-skills`.

## Capabilities

### New Capabilities
- `project-identity`: identidad LibreSeal, aviso de no afiliación, atribución y cumplimiento de licencias (ausencia de código `ee/`).
- `feature-availability`: disponibilidad de funciones por edición LibreSeal sin planes, cuotas, licencias ni facturación; tratamiento de funciones no disponibles y de controles de seguridad sin verificador.
- `self-hosted-deployment`: instalación reproducible con Docker Compose desde código fuente, persistencia, copia/restauración y operación sin servicios de Phase ni telemetría.
- `secrets-management`: CRUD de secretos en proyectos (apps) y entornos desde UI y API, cuentas de servicio y denegación fuera de permisos (comportamiento existente que se fija como contrato).
- `cli`: CLI `libreseal` contra un servidor autoalojado: autenticación, selección de app/entorno, gestión, importación/exportación e inyección de secretos.
- `agent-skills`: skills para que agentes desplieguen y usen LibreSeal de forma segura.

### Modified Capabilities
_(ninguna: no existen specs previas en el proyecto)_

## Impact

- Backend: `backend/backend/{settings,schema,urls,quotas}.py`, `backend/graphene/{middleware,types}.py`, mutaciones de organización/cuentas/roles/equipos/entornos/SSO, `api/{config,models,signals}.py`, `api/views/{secrets,members,service_accounts,roles,sso}.py`, `api/utils/{sso.py,access/middleware.py}`, `rqworker`, tests que importan `ee/`.
- Frontend: página de entorno (secretos), integraciones, onboarding, ajustes de organización, diálogos de acceso, navbar, providers, Apollo; dependencias `posthog-js`, `@stripe/*` retiradas; recursos de marca.
- GraphQL/REST: campos existentes conservados; resolvers/rutas de funciones `ee/` devuelven error *feature unavailable* o se retiran del esquema (detallado en design).
- Despliegue: `docker-compose.yml`, `.env.example`, scripts nuevos en `scripts/`.
- CLI y skills: ver repos correspondientes.
