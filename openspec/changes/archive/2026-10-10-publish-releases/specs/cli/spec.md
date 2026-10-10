# Spec Delta

## MODIFIED Requirements

### Requirement: Comando libreseal
El CLI SHALL instalarse como el ejecutable `libreseal` y mostrar la marca LibreSeal en `--help` y `--version`. Su README SHALL documentar dos formas de instalarlo sin depender de publicaciones controladas por Phase: descargando un binario verificado de las releases de `Dos2Locos/libreseal-cli` y compilando desde el código fuente.

#### Scenario: Instalación desde fuente
- **WHEN** se ejecuta `./scripts/install-from-source.sh` en `libreseal-cli` según el README
- **THEN** queda disponible `libreseal --version` y `libreseal --help` muestra "LibreSeal"

#### Scenario: Instalación desde un binario publicado
- **WHEN** se siguen los pasos del README para descargar `libreseal_0.1.0_linux_amd64` de la release `v0.1.0`, verificar `checksums.txt` con cosign y `sha256sum` e instalarlo
- **THEN** `libreseal --version` muestra `0.1.0` y `libreseal --help` muestra "LibreSeal"

### Requirement: Actualización sin infraestructura de Phase
El CLI SHALL NOT descargar ni ejecutar scripts desde `pkg.phase.dev` ni actualizarse a sí mismo. `libreseal update` SHALL mostrar cómo actualizar desde las releases de `Dos2Locos/libreseal-cli` (binario verificado) o compilando desde un tag de ese repositorio.

#### Scenario: Comando update
- **WHEN** se ejecuta `libreseal update`
- **THEN** el CLI no realiza peticiones de red, no modifica el ejecutable y muestra las instrucciones de actualización de LibreSeal, que mencionan `https://github.com/Dos2Locos/libreseal-cli/releases`
