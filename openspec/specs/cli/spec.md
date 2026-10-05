# cli Specification

## Purpose
Define el CLI `libreseal` (repositorio `libreseal-cli`) para autenticarse contra un servidor LibreSeal autoalojado, seleccionar app y entorno, gestionar secretos e inyectarlos en procesos, manteniendo compatibilidad con el CLI de Phase.

## Requirements

### Requirement: Comando libreseal
El CLI SHALL instalarse como el ejecutable `libreseal`, mostrar la marca LibreSeal en `--help` y `--version`, y documentar su instalación compilando desde el código fuente sin depender de publicaciones controladas por Phase.

#### Scenario: Instalación desde fuente
- **WHEN** se ejecuta `./scripts/install-from-source.sh` en `libreseal-cli` según el README
- **THEN** queda disponible `libreseal --version` y `libreseal --help` muestra "LibreSeal"

### Requirement: Sin host por defecto de Phase Cloud
El CLI SHALL NOT usar `console.phase.dev` ni ningún dominio de Phase como host por defecto y SHALL exigir un host explícito por variable de entorno, flag o prompt.

#### Scenario: Autenticación sin host
- **WHEN** se ejecuta `libreseal auth --mode token` sin `LIBRESEAL_HOST`/`PHASE_HOST` y sin respuesta al prompt de host
- **THEN** el comando falla pidiendo la URL del servidor y no contacta con dominios de Phase

#### Scenario: Autenticación con token de cuenta de servicio
- **WHEN** se exportan `LIBRESEAL_HOST=https://localhost` y `LIBRESEAL_SERVICE_TOKEN=<token sintético válido>` y se ejecuta `libreseal apps list`
- **THEN** el comando lista las apps visibles para esa cuenta de servicio

### Requirement: Compatibilidad con el CLI de Phase
El CLI SHALL aceptar las variables `PHASE_HOST`, `PHASE_SERVICE_TOKEN` y `PHASE_VERIFY_SSL` como alias de `LIBRESEAL_HOST`, `LIBRESEAL_SERVICE_TOKEN` y `LIBRESEAL_VERIFY_SSL` (prevaleciendo las `LIBRESEAL_*`), y los ficheros `.phase.json` y la configuración existente con los mismos flags de subcomandos.

#### Scenario: Variables heredadas
- **WHEN** solo se definen `PHASE_HOST` y `PHASE_SERVICE_TOKEN` y se ejecuta `libreseal secrets list --app-id <id> --env development`
- **THEN** el comando funciona igual que con las variables `LIBRESEAL_*`

### Requirement: Gestión de secretos según permisos
El CLI SHALL conservar `apps list`, `init`, `secrets list|get|create|update|delete|import|export` con los flags existentes y SHALL mostrar el error del servidor cuando la operación no está permitida.

#### Scenario: Importación y exportación
- **WHEN** se ejecuta `libreseal secrets import fixture.env --env development` con valores sintéticos y luego `libreseal secrets export --env development --format json`
- **THEN** la exportación contiene las claves importadas

#### Scenario: Permiso denegado
- **WHEN** una cuenta de servicio de solo lectura ejecuta `echo x | libreseal secrets create LS_DENIED --env development`
- **THEN** el comando termina con código distinto de cero y un mensaje de permiso denegado

### Requirement: Inyección de secretos en procesos
`libreseal run '<comando>'` SHALL ejecutar el comando con los secretos como variables de entorno sin imprimir sus valores en la salida del CLI.

#### Scenario: Inyección sin exposición
- **WHEN** se ejecuta `libreseal run --env development 'sh -c "test \"$LS_TEST_KEY\" = \"$EXPECTED\" && echo MATCH"'` con `EXPECTED` igual al valor sintético
- **THEN** la salida contiene `MATCH` y no contiene el valor del secreto

### Requirement: Actualización sin infraestructura de Phase
El CLI SHALL NOT descargar ni ejecutar scripts desde `pkg.phase.dev`; la actualización SHALL documentarse mediante compilación desde una etiqueta de `Dos2Locos/libreseal-cli`.

#### Scenario: Comando update
- **WHEN** se ejecuta `libreseal update`
- **THEN** el CLI no realiza peticiones de red a dominios de Phase y muestra las instrucciones de actualización de LibreSeal

### Requirement: Funciones no disponibles en el servidor
Los subcomandos `dynamic-secrets` SHALL informar de forma clara cuando el servidor LibreSeal no ofrece la función, y `libreseal run` SHALL funcionar sin dynamic secrets.

#### Scenario: run sin dynamic secrets
- **WHEN** se ejecuta `libreseal run 'true'` contra LibreSeal
- **THEN** el comando termina con código 0 sin errores de leases
