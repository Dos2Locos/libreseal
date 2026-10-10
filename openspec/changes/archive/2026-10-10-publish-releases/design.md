# Design

## Context

Estado observado el 2026-10-10 (motivación en `proposal.md`):

- **Servidor (`Dos2Locos/libreseal`)**
  - `docker-compose.yml` construye `backend`, `frontend` y `nginx` con `build:` y las etiqueta como `libreseal/*:local`. `migrations`, `backend` y `worker` comparten la imagen del backend.
  - `nginx/default.conf` se monta desde el host. `nginx/real-ip.sh` ya está dentro de la imagen.
  - El frontend ya genera una imagen portable: compila con marcadores `BAKED_NEXT_PUBLIC_*` que `scripts/replace-variable.sh` sustituye al arrancar. No hace falta compilar por instalación.
  - `backend` y `frontend` se construyen con su subdirectorio como contexto, así que `LICENSE` y `NOTICE` (en la raíz) no entran en las imágenes.
  - La versión vive en `backend/version.txt` (`v0.1.0`, la expone `/health/`) y en `frontend/package.json` (`0.1.0`).
  - `scripts/libreseal-init.sh` genera `.env` a partir de `.env.example` y termina recomendando `docker compose up -d --build`.
  - La CI (`.github/workflows/main.yml`) tiene los jobs `guard`, `backend`, `frontend` y `compose-build`, todos con permisos `contents: read`. Las acciones están fijadas por SHA.
  - El fork tiene 210 tags heredados (hasta `v2.77.2`).
- **CLI (`Dos2Locos/libreseal-cli`)**
  - `.goreleaser.yaml` ya existe: release en borrador en `Dos2Locos/libreseal-cli`, binarios sin comprimir para 8 objetivos, `checksums.txt` y la versión inyectada por `-ldflags`.
  - No hay ningún workflow que lo ejecute. Las acciones de la CI usan etiquetas (`@v7`), no SHAs.
  - `scripts/install-from-source.sh` obtiene la versión con `git describe --tags --always`, que hoy devuelve un tag heredado. El fork tiene 52 tags heredados (hasta `v2.3.2`).
  - `libreseal update` solo imprime instrucciones para compilar desde un tag.
- **Skills (`Dos2Locos/libreseal-skills`)**: no tiene tags. El skill `docker-compose` usa `docker compose up -d --build`.
- **GitHub**
  - Repositorios públicos en plan free: los runners `ubuntu-24.04-arm` y los rulesets están disponibles.
  - `main` está protegida en los tres repositorios mediante `scripts/github/protect-main.sh`, cuyo modo por defecto es la comprobación.
  - No hay rulesets de tags.

## Goals / Non-Goals

**Goals:**
- Que un tag sea la única entrada para publicar, y que una release solo se publique desde un commit de `main` que ha pasado los mismos checks que una PR.
- Que lo publicado sea verificable por un tercero solo con herramientas públicas (`cosign`, `sha256sum`, `docker buildx imagetools`), sin claves que custodiar.
- Que los permisos de escritura (`packages`, `contents`, `id-token`) existan solo en los workflows de release y solo en los jobs que los necesitan.

**Non-Goals:**
- Construcciones reproducibles bit a bit.
- Automatizar el changelog o la publicación de la release: el borrador lo revisa y lo publica un mantenedor.
- Cambiar el contenido funcional de las imágenes, salvo añadir `LICENSE`, `NOTICE` y etiquetas OCI.

## Decisions

### 1. Borrar los tags heredados en lugar de convivir con ellos
Los tags heredados se borran por API (`DELETE /repos/{owner}/{repo}/git/refs/tags/{tag}`) de `libreseal` y `libreseal-cli`. Antes, la lista de nombres y SHAs se guarda en `validation.md`. En los clones locales, `CONTRIBUTING.md` indica `git config remote.upstream.tagOpt --no-tags` y `git fetch --prune --prune-tags origin`, para que un `git fetch upstream` no los vuelva a traer.

`install-from-source.sh` pasa a usar `git describe --tags --match 'v[0-9]*' --always` como protección adicional.

- *Alternativa: filtrar con `--match 'v0.*'` sin borrar.* Se descarta porque cada herramienta (goreleaser, GitHub «Latest», `git tag --sort`) tendría que filtrar, y en cuanto LibreSeal llegue a `v1`/`v2` chocaría con los tags del original.
- El borrado es irreversible en los forks, pero los tags siguen en `phasehq/*` y se pueden recrear desde la lista guardada.

### 2. `backend/version.txt` es la fuente de la versión
`backend/version.txt` (`vX.Y.Z[-rc.N]`) es la fuente; `frontend/package.json` (`X.Y.Z[-rc.N]`) y el tag por defecto del compose (`${LIBRESEAL_VERSION:-X.Y.Z[-rc.N]}`) son copias.

- Un script nuevo, `scripts/set-version.sh X.Y.Z`, actualiza las tres.
- `check-libreseal-guard.sh` falla si no coinciden.
- El workflow de release falla si el tag no coincide con `version.txt`.

Para validar sin quemar `v0.1.0`, el primer ciclo usa `0.1.0-rc.1`:
1. Una PR sube la versión a `0.1.0-rc.1`, se fusiona y se crea el tag.
2. Si la validación sale bien, otra PR la sube a `0.1.0` y se crea su tag.

- *Alternativa: derivar la versión del tag al construir.* Se descarta porque una compilación local desde `main` no sabría su versión y `/health/` mostraría algo distinto de lo publicado.

### 3. Workflow de release del servidor (`.github/workflows/release.yml`)
Se dispara con `push: tags: ['v*']`. Los permisos de nivel superior son `contents: read`. Tiene cinco jobs:

1. **`verify`**
   - Comprueba que el tag cumple `^v\d+\.\d+\.\d+(-rc\.\d+)?$`.
   - Comprueba que el commit es antecesor de `origin/main` (`git merge-base --is-ancestor`).
   - Comprueba que el tag coincide con `backend/version.txt`.
2. **`ci`**: llama a `main.yml`, que gana el disparador `workflow_call`. Así se reutilizan `guard`, `backend`, `frontend` y `compose-build` sin duplicarlos. `guard` cubre la comprobación de `ee/`.
3. **`build`** (`needs: [verify, ci]`)
   - Es una matriz `image × platform` sobre runners nativos: `ubuntu-24.04` para amd64 y `ubuntu-24.04-arm` para arm64.
   - Usa `docker/build-push-action` con `push-by-digest`, `sbom: true` y `provenance: mode=max`, y sube cada digest como artefacto.
   - Permisos: `packages: write`.
4. **`publish`**
   - Por imagen, crea el índice multiplataforma con `docker buildx imagetools create` y la etiqueta `X.Y.Z`. Añade `latest` solo si no es `-rc`.
   - Firma el digest del índice con `cosign sign --yes` (keyless).
   - Permisos: `packages: write` e `id-token: write`.
5. **`release`**
   - Genera el paquete de despliegue con `scripts/make-deploy-bundle.sh X.Y.Z` y su `checksums.txt`.
   - Crea la release en borrador con `gh release create --draft --verify-tag`, con `--prerelease` si es `-rc`.
   - Permisos: `contents: write`.

Todas las acciones se fijan por SHA, como en la CI. No se usan acciones de terceros para crear la release (basta `gh`).

- *Alternativa: un solo job con QEMU.* Se descarta porque `next build` emulado en arm64 tarda decenas de minutos y falla a menudo por memoria. Los runners arm nativos son gratuitos en repos públicos.
- *Alternativa: una clave de cosign en un secreto.* Se descarta porque la firma keyless evita custodiar y rotar claves, y la identidad (workflow + tag) es más fuerte que la posesión de una clave.

### 4. Imágenes: nombres, etiquetas OCI y licencia
- Nombres: `ghcr.io/dos2locos/libreseal-{backend,frontend,nginx}`.
- Cada imagen lleva las etiquetas `org.opencontainers.image.{source,version,revision,licenses=MIT,title,description}`. `source` vincula el paquete de GHCR con el repositorio. `description` incluye el aviso de no afiliación.
- `LICENSE` y `NOTICE` se copian a `/usr/share/libreseal/` desde un contexto de construcción adicional (`additional_contexts: repo=.` en compose y `build-contexts` en buildx). Así no cambia el contexto de `backend`/`frontend` ni su caché.

### 5. Compose por defecto con imágenes publicadas
- **`docker-compose.yml`**
  - Quita los `build:`.
  - Cada servicio propio usa `image: ghcr.io/dos2locos/libreseal-<svc>:${LIBRESEAL_VERSION:-X.Y.Z}`.
  - Se mantienen los nombres de contenedor, el volumen `libreseal-postgres-data` y la red, para que actualizar no toque los datos.
- **`docker-compose.build.yml`**
  - Añade los `build:` (con `additional_contexts`).
  - Vuelve a etiquetar como `libreseal/<svc>:local`, para no hacer pasar una compilación local por una imagen firmada.
  - Fija `pull_policy: build`.
- `.env.example` incluye `LIBRESEAL_VERSION` comentado, solo para quien quiera fijar otra versión. `libreseal-init.sh` no lo escribe, para que actualizar el checkout o el paquete actualice la versión.
- El job `compose-build` de la CI usa el override.
- *Alternativa: `docker-compose.release.yml` opcional.* Se descarta por decisión del usuario: el camino por defecto debe ser el que no compila.

### 6. Paquete de despliegue
`scripts/make-deploy-bundle.sh X.Y.Z` genera `libreseal-deploy-X.Y.Z.tar.gz` con:
- `docker-compose.yml` y `.env.example`;
- `nginx/default.conf`;
- `scripts/libreseal-{init,backup,restore}.sh`;
- `LICENSE`, `NOTICE` y un `DEPLOY.md` corto con los comandos.

Los scripts ya resuelven rutas con `ROOT` relativo, así que funcionan igual fuera del clon. El script falla si `X.Y.Z` no coincide con `version.txt`, y así no hace falta sustituir nada en el compose.

### 7. Release del CLI
`libreseal-cli/.github/workflows/release.yml` se dispara con `push: tags: ['v*']`:
1. **`verify`**: comprueba el formato del tag y que el commit es antecesor de `main`.
2. **`test`**: llama a `test.yml` con `uses:`.
3. **`goreleaser`**
   - Usa `goreleaser/goreleaser-action` fijada por SHA y ejecuta `release --clean`.
   - Permisos: `contents: write` e `id-token: write`.

En `.goreleaser.yaml`:
- un bloque `signs` que ejecuta `cosign sign-blob --bundle checksums.txt.sigstore.json` sobre `checksums.txt`;
- `release.extra_files` con `LICENSE`.

Fuera de goreleaser:
- `libreseal update` y el README añaden la descarga verificada.
- GitHub adjunta el código fuente de cada release, lo que cubre la oferta de código de la GPL-3.0.

### 8. Protección de tags
`scripts/github/protect-main.sh` se amplía para gestionar en `libreseal` y `libreseal-cli` un ruleset `release-tags`:
- objetivo `tag`, con `include: ["refs/tags/v*"]`;
- reglas `creation`, `update` y `deletion`;
- excepción solo para `RepositoryRole` admin (id 5), con `bypass_mode: always`.

Mantiene sus tres modos (comprobación por defecto, `--apply` y `--disable`). Se conserva el nombre del script porque la spec `continuous-integration` lo referencia; la ayuda indica que también cubre los tags.

## Risks / Trade-offs

- **[Riesgo] Los paquetes nuevos de GHCR en una organización nacen privados, y la API REST no permite cambiar su visibilidad.**
  → La primera release es una `-rc`. Tras publicarla, un admin marca los tres paquetes como públicos en la web; la tarea y `CONTRIBUTING.md` lo indican. Los siguientes pushes heredan la visibilidad.
- **[Riesgo] `imagetools create` podría perder las atestaciones (SBOM y procedencia) de cada plataforma al crear el índice.**
  → Se verifica en la release `-rc` con `imagetools inspect --format '{{ json .SBOM }}'`. Si se pierden, se construye cada imagen con `platforms: linux/amd64,linux/arm64` en un único job con builders remotos nativos.
- **[Riesgo] Cambio incompatible para instalaciones que usan `docker compose up -d --build`.**
  → La guía de migración del README se valida con una instancia creada desde el `main` anterior. Los datos no se tocan (mismo volumen y mismo `.env`). Para volver atrás basta con usar el override de compilación.
- **[Riesgo] Después de subir la versión en `main` y antes de crear el tag, el compose de `main` apunta a una imagen que aún no existe.**
  → La PR de subida de versión es la PR de release y el tag se crea justo después de fusionarla. La documentación recomienda desplegar desde el paquete o desde un tag, no desde `main`.
- **[Riesgo] Borrar los tags heredados es irreversible en el fork.**
  → Antes se guarda la lista de nombres y SHAs. Los tags siguen en `phasehq/*`.
- **[Trade-off] El `Dockerfile` del backend descarga el bundle de CA de AWS RDS al construir.** Es una entrada no fijada, así que la imagen no es reproducible bit a bit. Se deja fuera de alcance: la procedencia `mode=max` registra la URL.
- **[Trade-off] Hay más tiempo de CI por release**, porque se repiten los checks de la PR y se construyen seis imágenes por plataforma. Se acepta porque las releases son poco frecuentes.

## Migration Plan

1. Fusionar los cambios del servidor (compose, override, versión, guard, workflows, script de protección), del CLI (workflow, goreleaser, `install-from-source`, `update`) y de los skills (documentación), cada uno con su PR y sus checks en verde.
2. Guardar la lista de tags heredados y borrarlos en `libreseal` y `libreseal-cli`. Después, aplicar el ruleset de tags con `protect-main.sh --apply`.
3. Crear la versión `0.1.0-rc.1`:
   - en el servidor: PR con `scripts/set-version.sh 0.1.0-rc.1` y tag `v0.1.0-rc.1`;
   - en el CLI: tag `v0.1.0-rc.1` directamente.
4. Marcar los paquetes de GHCR como públicos y validar todos los escenarios contra la `-rc`.
5. Con la validación en verde y a petición del usuario, subir la versión a `0.1.0`, crear los tags `v0.1.0` y publicar los borradores.

**Vuelta atrás:**
- Las releases en borrador se pueden borrar.
- Las etiquetas de GHCR de una `-rc` se pueden borrar desde la web.
- Un usuario afectado vuelve a compilar con `-f docker-compose.build.yml`.
- Revertir las PRs devuelve el compose a compilar desde el código.

## Open Questions

- ¿Hace falta conservar las imágenes `-rc` en GHCR después de publicar `v0.1.0`? No afecta al diseño; se puede decidir al cerrar la validación.
