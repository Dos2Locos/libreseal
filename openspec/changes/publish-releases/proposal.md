# Proposal

## Why

Hoy la única forma de usar LibreSeal es compilarlo: el `docker-compose.yml` construye las imágenes en cada máquina (varios minutos y mucha RAM en el frontend, inviable en equipos pequeños de homelab) y el CLI exige Go y un clon del repositorio. Además, los forks arrastran los tags del proyecto original (`v2.77.2` en el servidor, `v2.3.2` en el CLI), así que `git describe` y `libreseal --version` muestran versiones de Phase en lugar de las de LibreSeal (`backend/version.txt` ya declara `v0.1.0`). Con la CI y la protección de `main` ya funcionando, falta poder publicar versiones verificables.

## What Changes

- **libreseal**: nuevo workflow de release que, al empujar un tag `vX.Y.Z` desde `main`, comprueba que coincide con la versión declarada en el código, pasa los mismos checks que la CI, construye las imágenes `backend`, `frontend` y `nginx` para `linux/amd64` y `linux/arm64`, las publica en `ghcr.io/dos2locos/`, las firma con cosign (sin claves, con la identidad OIDC del workflow) y les adjunta SBOM y procedencia. Crea una release de GitHub en borrador con un paquete de despliegue (compose, configuración de nginx y scripts de init, copia y restauración) y sus sumas de verificación.
- **libreseal** — **BREAKING**: `docker-compose.yml` pasa a usar por defecto las imágenes publicadas, fijadas a `LIBRESEAL_VERSION` (por defecto, la versión del propio repositorio). Compilar desde el código pasa a `docker compose -f docker-compose.yml -f docker-compose.build.yml up -d --build`. Las instalaciones existentes con `docker compose up -d --build` dejarán de compilar y descargarán imágenes; se documenta la migración (mismo volumen y mismo `.env`).
- **libreseal**: la versión se declara en un único sitio y la CI comprueba que `backend/version.txt`, `frontend/package.json` y el tag por defecto del compose coinciden.
- **libreseal-cli**: nuevo workflow que, al empujar un tag `vX.Y.Z`, ejecuta goreleaser (la configuración ya existe), adjunta los binarios a una release en borrador de `Dos2Locos/libreseal-cli` y firma `checksums.txt` con cosign. El README documenta la instalación desde un binario verificado, además de desde el código.
- **libreseal** y **libreseal-cli** — **BREAKING** para quien dependa de ellos: se borran de los forks `Dos2Locos` los tags heredados del proyecto original (siguen existiendo en `phasehq/console` y `phasehq/cli`). La numeración propia empieza en `v0.1.0` en ambos repositorios.
- **libreseal** y **libreseal-cli**: una regla de GitHub limita la creación, modificación y borrado de tags `v*` a los administradores; el script `scripts/github/protect-main.sh` la aplica y la verifica.
- **libreseal-skills**: el skill `docker-compose` y sus referencias pasan a desplegar con las imágenes publicadas y mantienen la compilación desde el código como alternativa, en línea con el README de `libreseal`.

Fuera de alcance:
- Publicar en gestores de paquetes (Homebrew, apt, Scoop, AUR), Docker Hub o cualquier registro distinto de GHCR.
- Imágenes para arquitecturas distintas de `amd64` y `arm64`, y binarios del CLI más allá de los objetivos que ya define `.goreleaser.yaml`.
- Publicar automáticamente la release: queda en borrador hasta que un mantenedor la revisa y la publica.
- Actualización automática del servidor o del CLI (`libreseal update` sigue mostrando solo instrucciones).
- Releases de `libreseal-skills`, que se instalan desde el repositorio.
- Cambiar las imágenes de terceros (`postgres`, `redis`) o la descarga del bundle de CA de AWS RDS en el `Dockerfile` del backend.

## Capabilities

### New Capabilities
- `release-publishing`: cómo se versionan, construyen, firman y publican las imágenes del servidor y los binarios del CLI, quién puede crear tags de release y cómo un usuario verifica lo que descarga.

### Modified Capabilities
- `self-hosted-deployment`: la instalación reproducible pasa de compilar desde el código a usar imágenes publicadas y fijadas a una versión, manteniendo la compilación desde el código como alternativa documentada.
- `cli`: la actualización del CLI se documenta también mediante binarios publicados y verificables en `Dos2Locos/libreseal-cli`, no solo compilando desde un tag.

## Impact

- **libreseal**: `.github/workflows/` (nuevo workflow de release; `compose-build` de la CI pasa a usar el override de compilación), `docker-compose.yml`, nuevo `docker-compose.build.yml`, `scripts/libreseal-init.sh` y `.env.example` (siguiente paso sin `--build`; `LIBRESEAL_VERSION` opcional), `scripts/check-libreseal-guard.sh` (coherencia de versiones), `scripts/github/protect-main.sh` (regla de tags), `README.md` y `CONTRIBUTING.md` (proceso de release y verificación).
- **libreseal-cli**: nuevo workflow de release, `.goreleaser.yaml` (firma de checksums, `LICENSE` en la release), `scripts/install-from-source.sh` (versión correcta tras borrar los tags heredados) y `README.md`.
- **libreseal-skills**: `docker-compose/SKILL.md` y `docker-compose/refs/`.
- **GitHub**: paquetes públicos en `ghcr.io/dos2locos/libreseal-{backend,frontend,nginx}`, permisos `packages: write`, `id-token: write` y `contents: write` solo en los workflows de release, regla de protección de tags y borrado de los tags heredados (irreversible en los forks; recuperable desde los repositorios originales).
- **Código `ee/`**: ninguna dependencia afectada. Las imágenes se construyen desde el árbol de LibreSeal, que no contiene `ee/`, y el workflow de release ejecuta `scripts/check-libreseal-guard.sh` antes de construir, así que una imagen no se publica si reaparece código `ee/`. El CLI y los skills no tienen código `ee/`.
- **Licencias**: hoy las imágenes no incluyen `LICENSE` ni `NOTICE`, porque `backend` y `frontend` se construyen con su subdirectorio como contexto. Las imágenes publicadas los incluirán (MIT), junto con las etiquetas OCI de licencia y de origen. Los binarios del CLI son GPL-3.0: la release incluye `LICENSE` y el código fuente correspondiente al tag (los archivos de código que GitHub adjunta a cada release).
