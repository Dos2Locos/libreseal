# self-hosted-deployment Specification

## Purpose
Garantiza que LibreSeal se instala, arranca, persiste, se copia y se restaura de forma reproducible con Docker Compose desde su propio código fuente, sin cuentas ni servicios comerciales de Phase.

## Requirements

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

### Requirement: Enrutado interno aislado de redes compartidas
El nginx y el frontend de LibreSeal SHALL localizar el backend y el frontend por los nombres `libreseal-backend` y `libreseal-frontend`, definidos en la red interna del stack. Conectar el stack a una red compartida con servicios llamados `backend` o `frontend` SHALL NOT desviar ninguna petición a esos servicios.

#### Scenario: Red compartida con servicios homónimos
- **WHEN** con LibreSeal en marcha se crea una red Docker `shared-test` con dos contenedores de prueba con alias `backend` y `frontend` que responden siempre `IMPOSTOR`, se conecta `libreseal-nginx` a esa red y se ejecuta 20 veces `curl -sk https://localhost/service/health/` y `curl -sk https://localhost/login`
- **THEN** las 20 respuestas de salud contienen la versión de LibreSeal, las 20 de `/login` sirven la página de LibreSeal y ninguna contiene `IMPOSTOR`

#### Scenario: Llamadas del frontend al backend
- **WHEN** en esa misma situación se conecta también `libreseal-frontend` a `shared-test` y se inicia sesión en la UI y se lista una app
- **THEN** la sesión y el listado funcionan, y los contenedores de prueba no registran ninguna petición

#### Scenario: Guard ante nombres genéricos
- **WHEN** una PR cambia `nginx/default.conf` para que vuelva a usar `http://backend:8000`, o `docker-compose.yml` para que `BACKEND_API_BASE` vuelva a `http://backend:8000`
- **THEN** el check `guard` falla e indica el fichero y la línea

#### Scenario: Configuración antigua sigue funcionando
- **WHEN** una instancia actualizada a la versión con este cambio usa un `nginx/default.conf` anterior que apunta a `backend:8000` y `frontend:3000`, sin conectarse a redes compartidas
- **THEN** `curl -sk https://localhost/service/health/` devuelve la versión y la UI funciona
