# Spec Delta

## Purpose

Define los skills que permiten a agentes de IA desplegar y usar LibreSeal de forma segura contra un servidor configurable, sin exponer secretos ni usar credenciales de administrador.

## ADDED Requirements

### Requirement: Skill de despliegue con Docker Compose
`libreseal-skills` SHALL incluir un skill `docker-compose` que despliegue LibreSeal desde `Dos2Locos/libreseal` con los scripts del repositorio, sin imágenes `phasehq/*` ni documentación de Phase como fuente de instrucciones.

#### Scenario: Instrucciones verificables
- **WHEN** un agente sigue el skill `docker-compose` en una máquina con Docker
- **THEN** los comandos del skill coinciden con los del README de `libreseal` y la instancia arranca

#### Scenario: Sin referencias a Phase Cloud
- **WHEN** se ejecuta `grep -rnE "phasehq/(frontend|backend)|console\.phase\.dev|pkg\.phase\.dev" docker-compose/` en `libreseal-skills`
- **THEN** la salida está vacía

### Requirement: Skill de uso seguro por agentes
LibreSeal SHALL proporcionar un skill de uso, distribuido con el CLI (`libreseal ai skill`) y referenciado desde `libreseal-skills`, cuyos ejemplos usen comandos reales del CLI y host configurable.

#### Scenario: Skill sincronizado con el CLI
- **WHEN** se extraen los comandos `libreseal ...` del skill y se ejecuta cada uno con `--help`
- **THEN** todos los comandos y flags existen en el CLI

### Requirement: Secretos fuera de prompts, logs y ficheros versionados
Los skills SHALL indicar a los agentes que usen `libreseal run` para inyectar secretos, SHALL prohibir imprimir valores, redirigir exportaciones a ficheros o escribir secretos en ficheros versionados, y el CLI SHALL bloquear `printenv`/`env`/`export`/`set` dentro de `libreseal run` y `libreseal shell` en modo agente.

#### Scenario: Bloqueo en modo agente
- **WHEN** con `CLAUDECODE=1` en el entorno se ejecuta `libreseal run 'printenv'`
- **THEN** el CLI rechaza el comando sin mostrar valores

#### Scenario: El bloqueo no es la frontera de seguridad
- **WHEN** se lee el skill de uso
- **THEN** indica que la detección de agentes es una defensa en profundidad eludible y que la protección efectiva es el token de mínimo privilegio y los secretos `sealed`

### Requirement: Identidad de mínimo privilegio para agentes
Los skills SHALL indicar el uso de una cuenta de servicio dedicada con acceso limitado a la app y entorno necesarios y token suministrado por el usuario mediante variable de entorno, y SHALL NOT recomendar tokens de usuario o de administrador como configuración habitual.

#### Scenario: Ejemplo reproducible de agente
- **WHEN** se ejecuta el script de ejemplo del skill (`examples/agent-demo.sh`) con `LIBRESEAL_HOST` y `LIBRESEAL_SERVICE_TOKEN` de una cuenta de servicio limitada a `demo/Development`
- **THEN** el script lista apps, ejecuta un proceso con un secreto inyectado comprobando su presencia sin imprimirlo, y demuestra que el acceso a `Production` se deniega

### Requirement: Atribución y licencia de los skills
`libreseal-skills` SHALL conservar la licencia MIT y el copyright de Phase, y el skill embebido en el CLI SHALL permanecer bajo GPL-3.0.

#### Scenario: Licencias
- **WHEN** se inspeccionan `libreseal-skills/LICENSE` y `libreseal-cli/LICENSE`
- **THEN** conservan MIT (con copyright de Phase) y GPL-3.0 respectivamente
