# Spec Delta

## MODIFIED Requirements

### Requirement: Instalación reproducible desde código fuente
El `docker-compose.yml` de `Dos2Locos/libreseal` SHALL usar por defecto las imágenes publicadas en `ghcr.io/dos2locos/`, fijadas a `LIBRESEAL_VERSION` (por defecto, la versión del repositorio), sin compilar nada. El repositorio SHALL incluir `docker-compose.build.yml` para compilar las mismas imágenes desde el código, y un script de inicialización que genere `.env` con secretos aleatorios únicos.

#### Scenario: Instalación limpia
- **WHEN** en un clon limpio en el tag `v0.1.0` se ejecuta `./scripts/libreseal-init.sh` y después `docker compose up -d`
- **THEN** se descargan las imágenes `0.1.0` de `ghcr.io/dos2locos/`, no se compila ninguna imagen, todos los servicios quedan en estado `running`/`healthy`, las migraciones terminan con éxito y `https://localhost/` sirve la pantalla de inicio de sesión de LibreSeal

#### Scenario: Instalación limpia desde el código
- **WHEN** en un clon limpio se ejecuta `./scripts/libreseal-init.sh` y después `docker compose -f docker-compose.yml -f docker-compose.build.yml up -d --build`
- **THEN** las imágenes se construyen desde el código del repositorio, todos los servicios quedan en estado `running`/`healthy` y `https://localhost/` sirve la pantalla de inicio de sesión de LibreSeal

#### Scenario: Actualización de una instalación compilada
- **WHEN** una instancia creada con `docker compose up -d --build` antes de este cambio se actualiza siguiendo la guía de migración del README, conservando su `.env` y su volumen
- **THEN** la instancia arranca con las imágenes publicadas y los usuarios, apps y secretos siguen disponibles con sus valores

#### Scenario: Secretos no fijos
- **WHEN** se ejecuta `./scripts/libreseal-init.sh` dos veces en directorios distintos
- **THEN** los valores de `SECRET_KEY`, `SERVER_SECRET`, `NEXTAUTH_SECRET` y `DATABASE_PASSWORD` difieren entre ambos `.env` y ninguno coincide con valores de ejemplo publicados

#### Scenario: Sin sobrescritura
- **WHEN** se ejecuta `./scripts/libreseal-init.sh` con un `.env` ya existente
- **THEN** el script no modifica el `.env` y termina indicando que ya existe
