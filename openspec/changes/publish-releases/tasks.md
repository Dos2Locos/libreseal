# Tasks

`main` está protegida en los tres repositorios: cada grupo de cambios va en su propia rama y PR, con los checks obligatorios en verde.

Las tareas que borran tags, publican en GHCR o crean releases tienen efectos fuera del repositorio. Antes de ejecutarlas se pide confirmación expresa al usuario.

## 1. Versión única del servidor

- [x] 1.1 Rama `feat/publish-releases` en `libreseal`. Crear `scripts/set-version.sh X.Y.Z[-rc.N]`, que actualiza tres sitios:
  - `backend/version.txt` (`vX.Y.Z`);
  - `frontend/package.json` (`X.Y.Z`);
  - el valor por defecto de `LIBRESEAL_VERSION` en `docker-compose.yml`.

  Rechaza versiones con formato inválido. Añadir `scripts/tests/test-set-version.sh`. Verificar:
  - el test pasa sobre una copia temporal del repositorio;
  - `scripts/set-version.sh 1.2` falla con código distinto de 0.
- [x] 1.2 Ampliar `scripts/check-libreseal-guard.sh` para que falle si las tres versiones no coinciden, indicando los valores encontrados, y llamar al test de 1.1 desde el job `guard`. Verificar:
  - el guard pasa en el árbol actual;
  - falla tras cambiar solo `backend/version.txt` a `v0.2.0` en una copia temporal (escenario "Versiones desalineadas").

## 2. Imágenes y compose

- [x] 2.1 Añadir `LICENSE`, `NOTICE` y las etiquetas OCI (decisión 4 de `design.md`) a los `Dockerfile` de `backend`, `frontend` y `nginx`, usando el contexto adicional `repo`. Verificar con `docker buildx build --build-context repo=. ...` de cada imagen y comprobando dos cosas:
  - `docker run --rm --entrypoint cat <img> /usr/share/libreseal/NOTICE` muestra el aviso;
  - `docker inspect` muestra `org.opencontainers.image.licenses=MIT`.
- [x] 2.2 Reescribir `docker-compose.yml` con imágenes `ghcr.io/dos2locos/libreseal-<svc>:${LIBRESEAL_VERSION:-0.1.0}` y sin `build:`. Crear `docker-compose.build.yml` con los `build:`, `additional_contexts`, las etiquetas `libreseal/<svc>:local` y `pull_policy: build`. Añadir `LIBRESEAL_VERSION` comentado a `.env.example` y cambiar el siguiente paso que imprime `libreseal-init.sh` a `docker compose up -d`. Verificar:
  - `docker compose config` y `docker compose -f docker-compose.yml -f docker-compose.build.yml config` son válidos;
  - `scripts/tests/test-libreseal-init.sh` pasa;
  - el guard de 1.2 pasa.
- [x] 2.3 Cambiar el job `compose-build` de `.github/workflows/main.yml` para que use el override. Añadir el disparador `workflow_call`. Actualizar el comentario de cabecera, porque la publicación vive en `release.yml`. Verificar que el YAML es válido y que, en local, `docker compose -f docker-compose.yml -f docker-compose.build.yml build` termina con éxito.
- [x] 2.4 Validación local desde el código: con un `.env` nuevo de `libreseal-init.sh`, ejecutar `docker compose -f docker-compose.yml -f docker-compose.build.yml up -d --build` y comprobar:
  - todos los servicios en estado `running`/`healthy`;
  - `curl -sk https://localhost/service/health/` devuelve `v0.1.0`;
  - `https://localhost/` sirve el login de LibreSeal.

  Es el escenario "Instalación limpia desde el código". Bajar la instancia al terminar.

## 3. Workflow de release del servidor

- [x] 3.1 Crear `scripts/make-deploy-bundle.sh X.Y.Z` (contenido según la decisión 6). Falla si `X.Y.Z` no coincide con `backend/version.txt`. Añadir `scripts/tests/test-deploy-bundle.sh`, que comprueba el contenido del tar y el fallo con una versión distinta. Verificar con el test y `shellcheck`.
- [x] 3.2 Crear `.github/workflows/release.yml` con los jobs `verify`, `ci`, `build`, `publish` y `release` de la decisión 3. Debe cumplir:
  - permisos mínimos por job;
  - acciones fijadas por SHA (resolver con `gh api repos/<owner>/<action>/git/ref/tags/<tag>`);
  - etiqueta `latest` solo para versiones sin `-rc`;
  - `--prerelease` para las `-rc`.

  Verificar:
  - el YAML es válido;
  - `actionlint` sin errores (si no está instalado, usar su imagen Docker fijada por digest);
  - la lógica de `verify` probada en local con un script equivalente, contra un tag que no coincide y un commit fuera de `main`.
- [x] 3.3 Documentar en `README.md` tres cosas:
  - la instalación con el paquete de despliegue y desde el clon (`docker compose up -d`);
  - la compilación con el override;
  - la verificación con `cosign verify` y `sha256sum -c`.

  Documentar también la guía de migración desde instalaciones compiladas: `git pull`, `docker compose pull`, `docker compose up -d`, y borrar las imágenes `libreseal/*:local` antiguas. Documentar en `CONTRIBUTING.md` el proceso de release (`set-version.sh`, PR, tag) y la visibilidad de los paquetes de GHCR. Verificar que los comandos del README coinciden con los scripts y ficheros reales: revisarlos con `grep` contra el árbol.
- [x] 3.4 Abrir la PR de `feat/publish-releases`. Verificar que `gh pr checks` muestra `guard`, `backend`, `frontend` y `compose-build` en verde.

## 4. Release del CLI

- [x] 4.1 [cli] Rama `feat/publish-releases`. Cambiar `scripts/install-from-source.sh` a `git describe --tags --match 'v[0-9]*' --always --dirty`. Actualizar el texto de `libreseal update` para que mencione `https://github.com/Dos2Locos/libreseal-cli/releases` (binario verificado o compilación desde un tag) y su test, si existe. Verificar:
  - `go test ./...` en `src`;
  - `libreseal update` sin red (por ejemplo, con `HTTPS_PROXY=http://127.0.0.1:9`) muestra la URL y termina con 0.
- [x] 4.2 [cli] Añadir a `.goreleaser.yaml` el bloque `signs` (cosign `sign-blob --bundle checksums.txt.sigstore.json` sobre `checksums.txt`) y `release.extra_files` con `LICENSE`. Verificar con `goreleaser check` y `goreleaser release --snapshot --clean --skip=sign,publish`. Este último debe generar los 8 binarios, y `dist/libreseal_linux_amd64_v1/libreseal --version` (o la ruta equivalente) debe mostrar la versión del snapshot.
- [x] 4.3 [cli] Crear `.github/workflows/release.yml` con:
  - `verify` (formato del tag y ancestro de `main`);
  - `test` (`uses: ./.github/workflows/test.yml`);
  - `goreleaser`, con `contents: write`, `id-token: write`, acciones fijadas por SHA y `cosign-installer`.

  Verificar que el YAML es válido y `actionlint` no da errores.
- [x] 4.4 [cli] Documentar en el README la instalación desde un binario: descarga, `cosign verify-blob` con la identidad del workflow, `sha256sum -c --ignore-missing` y copia al `PATH`. Mantener la compilación desde el código. Abrir la PR y verificar que todos los checks obligatorios del CLI están en verde.

## 5. Skills

- [x] 5.1 [skills] Rama `docs/published-images`. Cambiar `docker-compose/SKILL.md` y `docker-compose/refs/*.md`:
  - despliegue por defecto con imágenes publicadas (`docker compose up -d`, o el paquete de la release);
  - actualización con `docker compose pull`;
  - compilación con `-f docker-compose.build.yml` como alternativa.

  Revisar los síntomas de troubleshooting que asumen `--build`. Verificar:
  - `scripts/validate-skills.sh` pasa;
  - `grep -rnE "phasehq/(frontend|backend)|console\.phase\.dev|pkg\.phase\.dev" docker-compose/` está vacío;
  - los comandos coinciden con el README de `libreseal` de 3.3.
- [x] 5.2 [skills] Abrir la PR y verificar que el check `validate` está en verde.

## 6. Tags y protección

- [x] 6.1 Ampliar `scripts/github/protect-main.sh` con el ruleset `release-tags` para `libreseal` y `libreseal-cli` (decisión 8) en los tres modos, y actualizar su ayuda. Verificar:
  - `shellcheck`;
  - en modo comprobación, el script informa de que falta la regla de tags sin cambiar nada.

  Incluirlo en la PR de 3.4 antes de fusionarla.
- [ ] 6.2 Con confirmación del usuario, fusionar las PRs de 3.4, 4.4 y 5.2 con sus checks en verde. Verificar con `gh run list --branch main` en verde en los tres repositorios.
- [ ] 6.3 Con confirmación del usuario, guardar en `validation.md` la lista de tags heredados (`git ls-remote --tags`, nombre y SHA) de `libreseal` y `libreseal-cli`, y borrarlos por API. Verificar el escenario "Sin tags heredados": `git ls-remote --tags` vacío en ambos. Documentar en `CONTRIBUTING.md` del servidor y del CLI cómo limpiar los clones locales (`git fetch --prune --prune-tags origin`, `remote.upstream.tagOpt --no-tags`). Aplicarlo al clon local.
- [ ] 6.4 Aplicar el ruleset con `protect-main.sh --apply`. Verificar el escenario "Regla de tags configurada" con `gh api repos/Dos2Locos/<repo>/rulesets/<id>`, y comprobar que el modo comprobación termina con 0.

## 7. Release candidata y validación

- [ ] 7.1 Servidor: PR con `scripts/set-version.sh 0.1.0-rc.1`. Con los checks en verde y la confirmación del usuario, fusionarla y empujar el tag `v0.1.0-rc.1`. Verificar:
  - el workflow `release.yml` termina en verde;
  - existe una release en borrador marcada como prerelease, con `libreseal-deploy-0.1.0-rc.1.tar.gz` y `checksums.txt`.
- [ ] 7.2 Marcar como públicos en la web de GitHub (lo hace un admin) los paquetes `libreseal-backend`, `libreseal-frontend` y `libreseal-nginx`. Verificar con `docker logout ghcr.io` y `docker pull ghcr.io/dos2locos/libreseal-backend:0.1.0-rc.1` sin credenciales.
- [ ] 7.3 Verificar las imágenes publicadas:
  - `imagetools inspect` muestra `linux/amd64` y `linux/arm64` en las tres;
  - `cosign verify` con la identidad del workflow del tag termina con éxito en las tres;
  - el SBOM SPDX está presente por plataforma;
  - `/usr/share/libreseal/NOTICE` está presente;
  - `latest` no existe o no cambia.

  Si el SBOM no aparece, aplicar la mitigación de `design.md`, repetir con `-rc.2` y anotar la causa.
- [ ] 7.4 Comprobar los rechazos en el servidor con tags `-rc` desechables:
  - un tag cuyo `version.txt` no coincide;
  - un tag sobre un commit de una rama sin fusionar.

  En ambos casos, `release.yml` debe fallar en `verify` y no debe aparecer ninguna etiqueta nueva en GHCR. Borrar los tags y ejecuciones de prueba.
- [ ] 7.5 Despliegue desde el paquete en un directorio sin clon:
  - descargar los adjuntos y ejecutar `sha256sum -c checksums.txt`;
  - descomprimir, ejecutar `./scripts/libreseal-init.sh` y `docker compose up -d`;
  - comprobar que no se compila nada, que los servicios están `healthy`, que `/service/health/` devuelve `v0.1.0-rc.1` y que el login de LibreSeal carga;
  - crear una app y un secreto sintético, y leerlo con el CLI de 7.6.

  Bajar la instancia al terminar.
- [ ] 7.6 [cli] Con confirmación del usuario, empujar el tag `v0.1.0-rc.1` en `libreseal-cli`. Verificar:
  - la release en borrador contiene 8 binarios, `checksums.txt`, `checksums.txt.sigstore.json` y `LICENSE`;
  - `cosign verify-blob` y `sha256sum -c --ignore-missing` pasan;
  - `libreseal_0.1.0-rc.1_<os>_<arch> --version` muestra `0.1.0-rc.1`;
  - desde un clon en el tag, `install-from-source.sh` produce la misma versión.
- [ ] 7.7 Migración de una instalación compilada:
  - levantar una instancia desde el `main` anterior a este cambio con `docker compose up -d --build` y un secreto sintético;
  - seguir la guía de migración del README hacia `0.1.0-rc.1`;
  - comprobar que el secreto se lee por la UI y por el CLI con el mismo valor.

  Bajar la instancia y borrar el volumen de prueba.
- [ ] 7.8 Escribir `validation.md` con los comandos ejecutados y sus resultados en 2.4, 6.3, 6.4 y 7.1–7.7, la lista de tags borrados y cualquier comprobación que no se haya podido ejecutar y por qué. Verificar con `openspec validate publish-releases --strict`.

## Workflow follow-up

- Con la validación en verde y a petición del usuario: subir la versión a `0.1.0` con `set-version.sh`, empujar los tags `v0.1.0` en el servidor y en el CLI, y publicar los borradores. Así se cubren los escenarios de la spec que nombran `0.1.0`.
- Decidir si se borran las imágenes `-rc` de GHCR (pregunta abierta en `design.md`).
- Archivar el cambio con `/opsx:archive publish-releases` en una rama con su PR.
