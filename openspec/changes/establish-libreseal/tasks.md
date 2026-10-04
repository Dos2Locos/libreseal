# Tasks

## 1. Línea base y retirada de `ee/`

- [x] 1.1 Ejecutar la suite de backend upstream (`pytest` en contenedor o venv) y `yarn test`/`tsc --noEmit` del frontend antes de tocar código; guardar el resultado como línea base en `openspec/changes/establish-libreseal/validation.md`
- [x] 1.2 Crear `backend/backend/edition.py` (registro `Feature`/`feature_enabled`, D2) con tests unitarios en `backend/tests/test_edition.py`; verificar con `pytest tests/test_edition.py`
- [x] 1.3 Reescribir `backend/backend/quotas.py` sobre `edition` sin consultar plan ni licencia; reemplazar `tests/test_quotas.py` y `tests/graphene/queries/test_quotas.py` por tests de "sin límites"; verificar con `pytest tests/test_quotas.py tests/graphene/queries/test_quotas.py`
- [x] 1.4 Desacoplar arranque y settings (`settings.py` sin `check_license`/`ee.settings`, `api/config.py`, `rqworker.py`) y verificar que `python manage.py check` pasa con `backend/ee` ausente
- [x] 1.5 Desacoplar esquema GraphQL, tipos, URLs, `api/views/secrets.py`, modelos, señales, mutaciones de cuentas/organización/miembros/cuentas de servicio y SSO (D4); verificar con `python manage.py check` y `python manage.py graphql_schema` (o equivalente) sin `ee`
- [x] 1.6 Sustituir las comprobaciones `org.plan` de roles, acceso y SSO por `feature_enabled`; añadir tests de creación de rol personalizado, equipo y entorno personalizado en organización por defecto; verificar con `pytest`
- [x] 1.7 Implementar fail-closed de políticas de red en ambos middlewares y bloqueo de creación/asignación (D5) con tests (cuenta con política → 403; sin política → RBAC); verificar con `pytest`
- [x] 1.8 `git rm -r backend/ee backend/tests/ee` y adaptar/eliminar los tests MIT que mockean `ee.*` (listados en `audit.md` §2), documentando cada eliminación; verificar `pytest` completo verde y `git ls-files | grep -E '(^|/)ee/'` vacío en backend

## 2. Frontend sin `ee/`, comercio ni telemetría

- [x] 2.1 Añadir el campo GraphQL aditivo `libresealFeatures` (D3) con test de backend; regenerar tipos del frontend (`yarn codegen` o el script del repo) y verificar que compila
- [x] 2.2 Crear `useFeature` y `UnavailableFeature`; sustituir todas las comprobaciones `organisation.plan`, `UpsellDialog`, `UpgradeRequestForm` y `PlanLabel` (lista en `audit.md` §3); verificar con `grep -rnE "UpsellDialog|UpgradeRequestForm|PlanLabel|ApiOrganisationPlanChoices" frontend/{app,components}` vacío o solo en tipos generados
- [x] 2.3 Retirar los consumidores de `@/ee/*` (página de entorno, integraciones de dynamic secrets y log streams, onboarding, `PlanInfo`) y `git rm -r frontend/ee`; verificar `tsc --noEmit` y `yarn build`
- [x] 2.4 Eliminar PostHog, Stripe, `StatusIndicator` de Phase y la consulta de releases a GitHub (D6), y sus variables `NEXT_PUBLIC_*` del Dockerfile/scripts; verificar con `grep -rniE "posthog|stripe|statuspage|api.github.com" frontend --exclude-dir=node_modules` sin coincidencias funcionales y `yarn test` verde

## 3. Identidad LibreSeal

- [ ] 3.1 Diseñar logotipo, wordmark y favicon propios en SVG/ICO en `frontend/public` y componentes de logo; documentar su origen y licencia en `frontend/public/brand/README.md`; verificar visualmente en `/login`
- [ ] 3.2 Cambiar textos visibles, títulos (`formatTitle`), metadatos y enlaces de documentación a LibreSeal y añadir el aviso de no afiliación en login; verificar con captura de `/login` y `grep -rn "docs.phase.dev" frontend/{app,components}` vacío
- [x] 3.3 Añadir `NOTICE` con atribución a Phase/Phi Security Inc. y licencias por componente, conservando `LICENSE`; verificar presencia y contenido

## 4. Despliegue autoalojado reproducible

- [ ] 4.1 Reescribir `docker-compose.yml` para construir desde fuente con nombres `libreseal-*` (D7) y actualizar `.env.example` sin secretos fijos; verificar con `docker compose config`
- [ ] 4.2 Crear `scripts/libreseal-init.sh` (genera `.env`, no sobrescribe) con test de shell (dos ejecuciones → secretos distintos; segunda ejecución sobre `.env` existente → sin cambios)
- [ ] 4.3 Crear `scripts/libreseal-backup.sh` y `scripts/libreseal-restore.sh`; verificar con un ciclo copia → borrado de volumen → restauración en la validación 7.6
- [ ] 4.4 Añadir comprobación de CI (workflow de GitHub Actions) que falle si reaparece `ee/` o dependencias `posthog-js`/`@stripe/*`; verificar ejecutando el script localmente

## 5. [cli] libreseal-cli

- [ ] 5.1 [cli] Renombrar comando y binario a `libreseal` (root, goreleaser, Dockerfile, install docs) y marca LibreSeal; verificar `go build ./... && ./libreseal --help`
- [ ] 5.2 [cli] Lectura central de `LIBRESEAL_*` con alias `PHASE_*`, sin host por defecto de Phase Cloud; tests unitarios de precedencia y de ausencia de default; verificar `go test ./...`
- [ ] 5.3 [cli] Sustituir `update`, `docs` y `console` para no usar dominios de Phase; verificar `go test ./...` y `grep -rn "phase.dev" src --include='*.go'` solo en tests/comentarios de atribución
- [ ] 5.4 [cli] Adaptar el skill embebido a `LIBRESEAL.md` (comandos `libreseal`, mínimo privilegio, aviso de detección eludible) y los nombres de instalación del skill; test que extrae comandos del skill y comprueba que existen en el árbol cobra
- [ ] 5.5 [cli] Mensaje claro para `dynamic-secrets` cuando el servidor responde 404 y `run` sin errores de leases; verificar con test o ejecución contra la instancia local
- [ ] 5.6 [cli] README: instalación desde fuente, configuración, actualización, compatibilidad con `phase` y licencia GPL-3.0/atribución; verificar que los comandos del README se ejecutan

## 6. [skills] libreseal-skills

- [ ] 6.1 [skills] Adaptar `docker-compose/` a LibreSeal (repo, scripts, verificación); verificar con `grep` de referencias a Phase Cloud vacío y recorrido real en la validación 7.9
- [ ] 6.2 [skills] Crear `libreseal-usage/` (SKILL.md + `examples/agent-demo.sh`) siguiendo el spec `agent-skills`; verificar con `shellcheck` si está disponible y ejecución en 7.9
- [ ] 6.3 [skills] README con instalación (`npx skills add Dos2Locos/libreseal-skills` y copia manual), estado de k8s/eks/aks, licencia MIT y atribución

## 7. Validación integrada (instancia local)

- [ ] 7.1 Instalación limpia en un clon nuevo: `libreseal-init.sh` + `docker compose up -d --build`; registrar estado de servicios y `curl -k https://localhost/` en `validation.md`
- [ ] 7.2 Registro de usuario con contraseña y creación de organización; CRUD de un secreto sintético en la UI con navegador automatizado; registrar capturas/resultados
- [ ] 7.3 Crear cuenta de servicio limitada a `demo/Development` (lectura y escritura) y otra de solo lectura; probar API: lectura 200, escritura 200/201, `Production` 403, escritura con solo lectura 403, token eliminado 401/403
- [ ] 7.4 Verificar sin cuotas: cuarto entorno personalizado, rol personalizado, equipo, 6 cuentas de servicio; y funciones no disponibles (UI y `GET /service/public/v1/secrets/dynamic/` → 404)
- [ ] 7.5 Persistencia: `docker compose down && docker compose up -d` y relectura del secreto por API y CLI
- [ ] 7.6 Copia y restauración: backup → `docker compose down -v` → up → restore → relectura por CLI
- [ ] 7.7 CLI contra la instancia: `auth --mode token`, `apps list`, `init`, `secrets create/list/get/update/delete`, `import/export`, `run` comprobando el valor sin imprimirlo; capturar la salida y verificar que el valor sintético no aparece (`grep -c`)
- [ ] 7.8 Sin servicios de Phase: capturar peticiones del navegador durante 7.2 y conexiones del backend (logs/`tcpdump` o proxy) y comprobar ausencia de dominios de Phase, PostHog, Stripe, statuspage y GitHub API
- [ ] 7.9 Skills: recorrido real del skill `docker-compose` (o de sus comandos) y ejecución de `agent-demo.sh` con `CLAUDECODE=1`, incluyendo el bloqueo de `printenv`
- [ ] 7.10 Ejecutar `openspec validate establish-libreseal --strict` y registrar la matriz verificada Console/CLI/skills en los README

## 8. Documentación y entrega

- [ ] 8.1 README de `libreseal`: propósito y estado real, relación con Phase y atribuciones, instalación de servidor y CLI, skills, permisos para apps y agentes, copia/restauración, compatibilidad y limitaciones (funciones no disponibles, historial con `ee/`), contribución vía OpenSpec; verificar que cada comando documentado se ejecutó en la sección 7
- [ ] 8.2 Commits pequeños por grupo, push de `feat/establish-libreseal` en los tres repos y PRs contra `main` de cada fork sin fusionar; enlazar los PRs entre sí
- [ ] 8.3 Proponer el siguiente cambio (`add-network-policy-enforcement`, sala limpia) como cambio OpenSpec separado en estado propuesto
