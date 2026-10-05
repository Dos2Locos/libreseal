# Spec Delta

## Purpose

Garantiza que LibreSeal se instala, arranca, persiste, se copia y se restaura de forma reproducible con Docker Compose desde su propio código fuente, sin cuentas ni servicios comerciales de Phase.

## ADDED Requirements

### Requirement: Instalación reproducible desde código fuente
El repositorio SHALL incluir un `docker-compose.yml` que construya las imágenes de backend y frontend desde el código del repositorio y un script de inicialización que genere `.env` con secretos aleatorios únicos.

#### Scenario: Instalación limpia
- **WHEN** en un clon limpio se ejecuta `./scripts/libreseal-init.sh` y después `docker compose up -d --build`
- **THEN** todos los servicios quedan en estado `running`/`healthy`, las migraciones terminan con éxito y `https://localhost/` sirve la pantalla de inicio de sesión de LibreSeal

#### Scenario: Secretos no fijos
- **WHEN** se ejecuta `./scripts/libreseal-init.sh` dos veces en directorios distintos
- **THEN** los valores de `SECRET_KEY`, `SERVER_SECRET`, `NEXTAUTH_SECRET` y `DATABASE_PASSWORD` difieren entre ambos `.env` y ninguno coincide con valores de ejemplo publicados

#### Scenario: Sin sobrescritura
- **WHEN** se ejecuta `./scripts/libreseal-init.sh` con un `.env` ya existente
- **THEN** el script no modifica el `.env` y termina indicando que ya existe

### Requirement: Operación sin servicios de Phase ni telemetría
Una instancia LibreSeal SHALL funcionar sin licencia, sin cuenta de Phase y sin acceso a dominios de Phase, y su frontend SHALL NOT enviar telemetría ni consultar servicios de estado o releases de terceros.

#### Scenario: Sin conexiones a Phase
- **WHEN** se completa el flujo de registro, creación de app, CRUD de secretos y uso del CLI registrando las peticiones del navegador y del backend
- **THEN** ninguna petición se dirige a `*.phase.dev`, `phase.statuspage.io`, `*.posthog.com`, `*.stripe.com` ni `api.github.com`

#### Scenario: Sin licencia configurada
- **WHEN** el backend arranca sin `PHASE_LICENSE_OFFLINE`
- **THEN** arranca sin errores de licencia y todas las funciones núcleo están disponibles

### Requirement: Persistencia tras reinicio
Los datos de LibreSeal SHALL persistir en un volumen con nombre a través de reinicios y recreación de contenedores.

#### Scenario: Reinicio
- **WHEN** se crea un secreto, se ejecuta `docker compose down` y luego `docker compose up -d`
- **THEN** el secreto sigue disponible con el mismo valor por UI, API y CLI

### Requirement: Copia y restauración
LibreSeal SHALL proporcionar scripts documentados para crear una copia de la base de datos y restaurarla en una instancia, y SHALL documentar que la copia sin las claves de usuario o la frase de recuperación no permite descifrar los secretos.

#### Scenario: Copia y restauración
- **WHEN** se ejecuta `./scripts/libreseal-backup.sh`, se elimina el volumen de datos, se recrea la instancia con el mismo `.env` y se ejecuta `./scripts/libreseal-restore.sh <fichero>`
- **THEN** los usuarios, apps, entornos y secretos vuelven a estar disponibles y el CLI lee el secreto de prueba con su valor original
