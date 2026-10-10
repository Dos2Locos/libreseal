# Spec Delta

## Purpose
Define cómo se numeran, construyen, firman y publican las versiones del servidor y del CLI de LibreSeal, quién puede crearlas y cómo un usuario verifica que lo que descarga procede de los repositorios de LibreSeal.

## ADDED Requirements

### Requirement: Numeración propia de versiones
`Dos2Locos/libreseal` y `Dos2Locos/libreseal-cli` SHALL numerar sus versiones con tags `vX.Y.Z` (SemVer, con sufijo `-rc.N` opcional para versiones previas), empezando en `v0.1.0`. Ninguno de los dos repositorios SHALL contener tags heredados del proyecto original.

#### Scenario: Sin tags heredados
- **WHEN** se ejecuta `git ls-remote --tags https://github.com/Dos2Locos/libreseal` y lo mismo para `libreseal-cli`
- **THEN** todos los tags listados son versiones de LibreSeal `v0.*` o posteriores, y no aparece `v2.77.2` en el servidor ni `v2.3.2` en el CLI

#### Scenario: Versión del CLI compilado desde el código
- **WHEN** en un clon de `libreseal-cli` en el tag `v0.1.0` se ejecuta `./scripts/install-from-source.sh` y luego `libreseal --version`
- **THEN** la versión mostrada es `0.1.0`

### Requirement: Versión única del servidor
La versión declarada en `backend/version.txt`, en `frontend/package.json` y en el tag de imagen por defecto de `docker-compose.yml` SHALL coincidir, y la CI SHALL fallar si no coinciden.

#### Scenario: Versiones desalineadas
- **WHEN** una PR cambia `backend/version.txt` a `v0.2.0` sin cambiar `frontend/package.json`
- **THEN** el check `guard` falla e indica las versiones encontradas

#### Scenario: Versión expuesta
- **WHEN** se consulta `curl -sk https://localhost/service/health/` en una instancia arrancada con las imágenes de `v0.1.0`
- **THEN** la respuesta contiene `"version": "v0.1.0"`

### Requirement: Publicación de imágenes del servidor
Al empujar un tag `vX.Y.Z` cuyo commit está en `main` y coincide con la versión declarada, `Dos2Locos/libreseal` SHALL publicar `ghcr.io/dos2locos/libreseal-backend`, `-frontend` y `-nginx` con la etiqueta `X.Y.Z` para `linux/amd64` y `linux/arm64`, solo si los checks de la CI pasan sobre ese commit.

#### Scenario: Release correcta
- **WHEN** un administrador empuja el tag `v0.1.0` sobre un commit de `main` con `backend/version.txt` igual a `v0.1.0`
- **THEN** `docker buildx imagetools inspect ghcr.io/dos2locos/libreseal-backend:0.1.0` lista las plataformas `linux/amd64` y `linux/arm64`, y lo mismo para `frontend` y `nginx`

#### Scenario: Tag que no coincide con la versión
- **WHEN** se empuja el tag `v0.1.1` sobre un commit cuyo `backend/version.txt` es `v0.1.0`
- **THEN** el workflow de release falla antes de construir y no se publica ninguna imagen con la etiqueta `0.1.1`

#### Scenario: Tag fuera de main
- **WHEN** se empuja un tag `vX.Y.Z` sobre un commit que no es antecesor de `main`
- **THEN** el workflow de release falla sin publicar imágenes

#### Scenario: Código ee/ en el tag
- **WHEN** el commit del tag contiene un fichero bajo un directorio `ee/`
- **THEN** el workflow de release falla en la comprobación de invariantes sin publicar imágenes

#### Scenario: Versión previa
- **WHEN** se empuja el tag `v0.2.0-rc.1`
- **THEN** se publican las imágenes con la etiqueta `0.2.0-rc.1` y la etiqueta `latest` no cambia

### Requirement: Firma y procedencia de las imágenes
Cada imagen publicada SHALL estar firmada con cosign sin claves mediante la identidad OIDC del workflow de release de `Dos2Locos/libreseal`, e incluir un SBOM y una atestación de procedencia. Las imágenes SHALL contener `LICENSE` y `NOTICE`.

#### Scenario: Verificación de la firma
- **WHEN** un usuario ejecuta `cosign verify ghcr.io/dos2locos/libreseal-backend:0.1.0 --certificate-identity-regexp '^https://github.com/Dos2Locos/libreseal/.github/workflows/release.yml@refs/tags/v' --certificate-oidc-issuer https://token.actions.githubusercontent.com`
- **THEN** la verificación termina con éxito

#### Scenario: SBOM disponible
- **WHEN** se ejecuta `docker buildx imagetools inspect ghcr.io/dos2locos/libreseal-frontend:0.1.0 --format '{{ json .SBOM }}'`
- **THEN** la salida contiene un SBOM SPDX no vacío por plataforma

#### Scenario: Licencia en la imagen
- **WHEN** se ejecuta `docker run --rm --entrypoint cat ghcr.io/dos2locos/libreseal-backend:0.1.0 /usr/share/libreseal/NOTICE`
- **THEN** la salida contiene el aviso de copyright de Phi Security Inc. y el de no afiliación de LibreSeal

### Requirement: Release del servidor con paquete de despliegue
Cada tag del servidor SHALL crear una release de GitHub en borrador que adjunte `libreseal-deploy-X.Y.Z.tar.gz` (compose, configuración de nginx y scripts de init, copia y restauración, con la versión fijada) y `checksums.txt`. Solo un mantenedor SHALL publicar el borrador.

#### Scenario: Despliegue desde el paquete
- **WHEN** en una máquina con Docker y sin clon del repositorio se descomprime `libreseal-deploy-0.1.0.tar.gz`, se ejecuta `./scripts/libreseal-init.sh` y luego `docker compose up -d`
- **THEN** se descargan las imágenes `0.1.0` de `ghcr.io/dos2locos/`, no se compila nada y `https://localhost/` sirve la pantalla de inicio de sesión de LibreSeal

#### Scenario: Integridad del paquete
- **WHEN** se descargan los adjuntos de la release y se ejecuta `sha256sum -c checksums.txt`
- **THEN** todas las comprobaciones devuelven `OK`

### Requirement: Publicación de binarios del CLI
Al empujar un tag `vX.Y.Z` cuyo commit está en `main` y cuyos tests pasan, `Dos2Locos/libreseal-cli` SHALL crear una release en borrador con los binarios `libreseal` de los objetivos de `.goreleaser.yaml`, `checksums.txt` firmado con cosign sin claves y `LICENSE`.

#### Scenario: Binario con la versión del tag
- **WHEN** se descarga `libreseal_0.1.0_linux_amd64` de la release `v0.1.0` y se ejecuta `./libreseal_0.1.0_linux_amd64 --version`
- **THEN** la salida muestra `0.1.0`

#### Scenario: Verificación del binario
- **WHEN** se ejecuta `cosign verify-blob checksums.txt --bundle checksums.txt.sigstore.json --certificate-identity-regexp '^https://github.com/Dos2Locos/libreseal-cli/.github/workflows/release.yml@refs/tags/v' --certificate-oidc-issuer https://token.actions.githubusercontent.com` y después `sha256sum -c checksums.txt --ignore-missing`
- **THEN** ambas comprobaciones terminan con éxito

#### Scenario: Tests en rojo
- **WHEN** se empuja un tag sobre un commit cuyos tests de Go fallan
- **THEN** el workflow falla y no se crea ninguna release con binarios

### Requirement: Tags de release protegidos
En `Dos2Locos/libreseal` y `Dos2Locos/libreseal-cli`, solo los administradores SHALL poder crear, mover o borrar tags `v*`. La regla SHALL poder reaplicarse y verificarse con el script de protección versionado en `Dos2Locos/libreseal`.

#### Scenario: Regla de tags configurada
- **WHEN** se consulta `gh api repos/Dos2Locos/<repo>/rulesets` y el detalle de la regla de tags de `libreseal` y de `libreseal-cli`
- **THEN** existe una regla activa sobre `refs/tags/v*` que impide crear, actualizar y borrar esos tags, y su única excepción es el rol de administrador del repositorio

#### Scenario: Comprobar la regla
- **WHEN** un administrador ejecuta `scripts/github/protect-main.sh` sin opciones (modo de comprobación)
- **THEN** el script informa de que la regla de tags `v*` está activa en ambos repositorios y termina con código 0
