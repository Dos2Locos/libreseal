# Design

## Context

Ver `proposal.md` (motivación) y `audit.md` (puntos de acoplamiento con referencias). Restricciones que condicionan el enfoque:

- El núcleo MIT importa `ee/` en ~40 puntos del backend, incluido el arranque (`settings.py:6` importa `check_license`) y el esquema GraphQL; borrar `ee/` sin más rompe el arranque.
- La lógica comercial está repartida: `backend/backend/quotas.py` más ~10 comprobaciones directas `org.plan == FREE_PLAN` en backend y ~20 `organisation.plan === ApiOrganisationPlanChoices.*` en frontend.
- Los modelos de las funciones `ee/` (`DynamicSecret`, `RotatingSecret`, `LogStream`, `NetworkAccessPolicy`, `ActivatedPhaseLicense`, campos `plan`/`pricing_version`) viven en `api/models.py` (MIT) con migraciones aplicadas; eliminarlos exigiría migraciones destructivas.
- El frontend se compila con tipos generados de GraphQL (`apollo/graphql.ts`, `codegen.ts`); retirar tipos del esquema obliga a regenerar.
- El CLI depende de `phasehq/golang-sdk` (MIT), que acepta host arbitrario: no hace falta fork del SDK.

## Goals / Non-Goals

**Goals:**
- Árbol y builds sin código `ee/`, con arranque y tests verdes.
- Una única fuente de verdad para la disponibilidad de funciones en backend y frontend.
- Mantener esquema de BD, contratos REST/GraphQL usados por CLI/SDKs y formatos criptográficos.

**Non-Goals:**
- Reescribir o renombrar paquetes Python/TS internos (`api`, `backend`) o variables `PHASE_*` del servidor.
- Eliminar modelos/migraciones de funciones no disponibles.
- Retirar el modo `APP_HOST=cloud` (queda sin uso y se documenta como no soportado).

## Decisions

### D1. Retirar `ee/` con `git rm`, no con exclusión en build
Se eliminan `backend/ee`, `frontend/ee` y `backend/tests/ee` del árbol. *Alternativa descartada*: mantenerlos y excluirlos vía `.dockerignore`/flags — seguiríamos redistribuyendo código no libre en cada clon y tarball, y es fácil reintroducirlo por error. Un test de CI (`git ls-files | grep '(^|/)ee/'` vacío) evita regresiones. El historial heredado queda tal cual (fork de GitHub); se documenta.

### D2. Módulo `backend/backend/edition.py` como registro de funciones
Define `Feature` (enum) y `feature_enabled(feature) -> bool`, con dos grupos fijos: núcleo (`CUSTOM_ROLES`, `TEAMS`, `CUSTOM_ENVIRONMENTS`, `SERVICE_ACCOUNTS`) siempre `True`; no disponibles (`DYNAMIC_SECRETS`, `SECRET_ROTATION`, `LOG_STREAMS`, `SCIM`, `ENTERPRISE_SSO`, `NETWORK_POLICIES`, `BILLING`, `LICENSING`) siempre `False`. `quotas.py` conserva sus funciones públicas (`can_add_app`, `can_add_account`, `can_add_environment(s)`, `can_use_*`) para no tocar los llamadores, pero delega en `edition` y deja de consultar `plan` o licencias. Las comprobaciones directas de `org.plan` en roles, acceso y middleware se sustituyen por `feature_enabled`. *Alternativas descartadas*: (a) fijar `plan="EN"` en todas las organizaciones — simula una licencia Enterprise y es lo que se quiere evitar; (b) variables de entorno por función — prometería funciones que no existen.

### D3. Exponer disponibilidad al frontend con un campo GraphQL aditivo
Se añade `libresealFeatures: [String!]!` (lista de funciones habilitadas) a la query raíz. El frontend usa un hook `useFeature(name)` en lugar de comparar planes. Cambio aditivo: no rompe clientes existentes. `PlanTypeEnum`, `organisation.plan` y `organisationPlan` se mantienen en el esquema (valores sin efecto) para compatibilidad; `organisationPlan` devuelve límites `null`.

### D4. Degradación de funciones `ee/`
- **Esquema GraphQL**: se eliminan los campos/mutaciones cuyo resolver está en `ee/` (dynamic secrets, rotation, log streams, SCIM, Stripe, licencias). `EnvironmentType.dynamicSecrets` y similares que el frontend consulta se conservan devolviendo lista vacía para no forzar reescrituras amplias; el resto se retira y se regeneran los tipos.
- **REST**: se elimina `v1/secrets/dynamic/` → 404; en `api/views/secrets.py` la rama de dynamic secrets se elimina y `include_dynamic_secrets` se ignora (sin cambiar el formato de respuesta de secretos estáticos).
- **Modelos/señales/arranque**: los *hooks* que llaman a `ee` (revocación de leases, cancelación de jobs de rotación/log streams, *sweeper*, verificador de licencias) se convierten en no-op documentados; como no se pueden crear objetos de esas funciones, solo afectan a datos heredados.
- **SSO**: se mantienen los proveedores OAuth del núcleo (Google, GitHub, GitLab en `api/views/sso.py` si su adaptador es MIT); se retiran del registro los adaptadores cuyo `adapter_module` apunta a `ee.*` (Entra ID, Okta, Google OIDC, JumpCloud, GitHub Enterprise).
- **Facturación**: las llamadas `update_stripe_*`/`create_stripe_customer`/`activate_license` desaparecen (solo se ejecutaban en nube o con licencia).
- **Frontend**: se eliminan las páginas/diálogos que importan `@/ee/*`; las entradas de menú de esas funciones muestran un componente `UnavailableFeature` ("No disponible en LibreSeal") sin CTA comercial.

### D5. Políticas de red: fallar cerrado
`feature_enabled(NETWORK_POLICIES)` es `False`. Las mutaciones de creación/asignación devuelven error. En ambos middlewares (GraphQL y REST), si la cuenta tiene políticas aplicables (propias o globales) se deniega con mensaje explícito; si no tiene, se continúa con RBAC. *Alternativa descartada*: ignorarlas como hace upstream en plan Free — un control configurado que deja de aplicarse en silencio es peor que un rechazo visible. *Alternativa pospuesta*: verificador propio en sala limpia (cambio `add-network-policy-enforcement`).

### D6. Telemetría y llamadas salientes del frontend
Se eliminan `posthog-js` y `@stripe/*` de `package.json`, `utils/posthog.ts`, `PostHogProvider`, `posthog.identify/reset`, el `StatusIndicator` de Phase en navbar/login (el componente de estado de *syncs* se conserva si es independiente), y `ReleaseInfo` pasa a mostrar la versión local sin consultar GitHub. Enlaces a `docs.phase.dev` → README/docs de LibreSeal. `NEXT_PUBLIC_POSTHOG_*`, `NEXT_PUBLIC_STRIPE_PUBLIC_KEY` y `NEXT_PUBLIC_SLACK_NOTIF_URL` se retiran de Dockerfile y scripts de sustitución.

### D7. Despliegue: compose desde fuente y scripts
`docker-compose.yml` usa `build:` para backend (también migraciones y worker, misma imagen `libreseal/backend:local`) y frontend (`libreseal/frontend:local`); nombres de contenedor/volumen/red con prefijo `libreseal`. **Compatibilidad**: el volumen pasa a `libreseal-postgres-data`; para migrar desde Phase se documenta copia/restauración (no se reutiliza el volumen `phase-postgres-data` implícitamente). `scripts/libreseal-init.sh` genera `.env` con `openssl rand -hex 32` y nunca sobrescribe. `scripts/libreseal-backup.sh` usa `pg_dump -Fc` desde el contenedor de postgres a `./backups/`; `libreseal-restore.sh` restaura con `pg_restore --clean --if-exists` con servicios de aplicación parados. Se añade `HEALTHCHECK`/`depends_on` adecuado si falta. El nginx con certificado autofirmado existente se conserva para `https://localhost`.

### D8. Marca
Logotipo y favicon nuevos en SVG propios (diseño original: sello/escudo geométrico), sustituyendo `LogoMark`/`LogoWordMark`, favicons y `formatTitle`. Textos visibles "Phase" → "LibreSeal" en UI; identificadores internos, nombres de paquetes y variables `PHASE_*` del servidor no cambian (compatibilidad). Aviso de no afiliación en login y README.

### D9. CLI: fork mínimo y compatible
En `libreseal-cli`: `rootCmd.Use = "libreseal"`, ASCII/description propios, binario de goreleaser `libreseal`; se elimina `PhaseCloudAPIHost` como default (prompt obligatorio, sin opción "Phase Cloud"); `LIBRESEAL_HOST`/`LIBRESEAL_SERVICE_TOKEN`/`LIBRESEAL_VERIFY_SSL` con precedencia sobre `PHASE_*` mediante una función de lectura central; `update` imprime instrucciones (`go install github.com/Dos2Locos/libreseal-cli/src@<tag>`) sin red; `docs`/`console` abren el README de LibreSeal y el host configurado. El *module path* Go se mantiene (`github.com/phasehq/cli`) en este cambio para minimizar el diff; se documenta y se pospone su renombrado. Config `~/.phase` y `.phase.json` se conservan. Skill embebido `PHASE.md` → `LIBRESEAL.md` con comandos `libreseal` y sección de mínimo privilegio. *Alternativa descartada*: wrapper sobre el binario `phase` — dependería de releases de Phase.

### D10. Skills
En `libreseal-skills`: adaptar `docker-compose/` a clonar `Dos2Locos/libreseal`, ejecutar los scripts del repo y verificar; nuevo skill `libreseal-usage/` breve que remite a `libreseal ai skill` como fuente versionada e incluye `examples/agent-demo.sh` (bash, sin imprimir valores; comprueba presencia con `test -n` y longitud). `k8s/eks/aks` se marcan como no soportados todavía en README (no se borran).

### D11. Matriz verificada
Se documenta en README de los tres repos la combinación verificada: `libreseal@<commit>` + `libreseal-cli@<commit>` (golang-sdk v2.4.1) + `libreseal-skills@<commit>`.

## Risks / Trade-offs

- [Retirar campos GraphQL rompe consultas del frontend] → regenerar tipos (`yarn codegen` contra el esquema local) y `yarn build`/`tsc` como puerta.
- [Tests MIT que mockean módulos `ee.*`] → eliminar los casos que prueban funcionalidad `ee/` y adaptar los que prueban núcleo; documentar en tasks cuáles.
- [Datos heredados de Phase con dynamic secrets/rotation activos] → no se revocan credenciales externas (AWS) al borrar; se documenta que antes de migrar hay que revocar leases en Phase.
- [Fail-closed de políticas de red bloquea a usuarios migrados] → mensaje explícito y procedimiento documentado para eliminar políticas vía Django admin/shell.
- [Divergencia con upstream dificulta *merges*] → cambios concentrados en módulos nuevos (`edition.py`, `useFeature`, `UnavailableFeature`) y en puntos de llamada; registrar en README el procedimiento de sincronización.
- [Build del frontend lento/pesado en máquinas pequeñas] → documentar requisitos (≥4 GB RAM para build) y permitir build en otra máquina.
- [La detección de agentes del CLI es eludible] → documentado; la defensa real es el token de mínimo privilegio.

## Migration Plan

1. Instancia nueva: `libreseal-init.sh` → `docker compose up -d --build`.
2. Desde Phase autoalojado: `pg_dump` en Phase → `libreseal-restore.sh` con `.env` que conserve `SECRET_KEY`/`SERVER_SECRET` originales → `migrate`. Revocar antes leases dinámicos y eliminar políticas de red si no se desea el bloqueo.
3. Rollback: restaurar la copia previa en la instancia anterior; el esquema de BD no cambia en este cambio, por lo que la copia es compatible en ambos sentidos.

## Open Questions

- Política de publicación de imágenes/binarios (GHCR, releases) — cambio separado; no afecta a este diseño.
