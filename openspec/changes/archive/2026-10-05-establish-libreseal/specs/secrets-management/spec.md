# Spec Delta

## Purpose

Fija como contrato el comportamiento heredado de gestión de secretos en apps y entornos desde la UI y la API, con cuentas de servicio de mínimo privilegio y denegación fuera de permisos.

## ADDED Requirements

### Requirement: CRUD de secretos desde la UI
Un usuario con permisos sobre un entorno SHALL poder crear, consultar, editar y eliminar secretos desde la interfaz web, con cifrado de extremo a extremo en el navegador.

#### Scenario: Ciclo completo en la UI
- **WHEN** un usuario crea la app `demo`, abre el entorno `Development`, crea `LS_TEST_KEY` con un valor sintético, lo edita y lo elimina
- **THEN** cada operación se refleja tras recargar la página y el valor nunca se envía en claro al backend

### Requirement: Apps y entornos
LibreSeal SHALL conservar apps con entornos por defecto (Development, Staging, Production) y entornos personalizados, y su selección en UI, API y CLI.

#### Scenario: Entornos por defecto
- **WHEN** se crea una app nueva desde la UI
- **THEN** la app tiene los entornos Development, Staging y Production

### Requirement: API para aplicaciones con cuentas de servicio
LibreSeal SHALL conservar la API pública `/service/public/v1/` y la autenticación `Authorization: Bearer ServiceAccount <token>` sin cambios de formato. El acceso a valores por la API REST requiere que la app tenga activado el cifrado del lado del servidor (SSE), como en upstream.

#### Scenario: Lectura con cuenta de servicio
- **WHEN** una cuenta de servicio con acceso de lectura a `demo/Development` llama a `GET /service/public/v1/secrets/?app_id=<id>&env=development` con su token
- **THEN** la respuesta es 200 y contiene `LS_TEST_KEY` descifrado

#### Scenario: Escritura con cuenta de servicio
- **WHEN** una cuenta de servicio con permiso de escritura envía `POST /service/public/v1/secrets/` con un secreto sintético
- **THEN** la respuesta es 200/201 y el secreto aparece en la UI

### Requirement: Denegación fuera de permisos
LibreSeal SHALL denegar cualquier acceso de una identidad a apps, entornos u operaciones no asignados por RBAC.

#### Scenario: Entorno no asignado
- **WHEN** una cuenta de servicio con acceso solo a `Development` solicita secretos de `Production`
- **THEN** la respuesta es 401 o 403 (contrato heredado: 401 "Service account cannot access this environment") y no se devuelven secretos

#### Scenario: Token revocado
- **WHEN** se usa un token de cuenta de servicio después de eliminarlo
- **THEN** la respuesta es 401/403

#### Scenario: Escritura con rol de solo lectura
- **WHEN** una cuenta de servicio con rol sin permiso de escritura intenta `POST /service/public/v1/secrets/`
- **THEN** la respuesta es 403 y el secreto no se crea

### Requirement: Recuperación de cuenta conservada
LibreSeal SHALL conservar el mecanismo existente de recuperación de cuenta mediante frase de recuperación sin cambiar algoritmos ni formatos.

#### Scenario: Recuperación
- **WHEN** un usuario usa su frase de recuperación en el flujo de recuperación de la UI
- **THEN** recupera el acceso a la organización y puede descifrar sus secretos
