# Spec Delta

## MODIFIED Requirements

### Requirement: Políticas de red fallan cerrado
LibreSeal SHALL permitir crear, editar y asignar políticas de red y SHALL aplicarlas: una cuenta (usuario o cuenta de servicio) con políticas aplicables (propias o globales de la organización) solo SHALL acceder desde una IP de cliente incluida en alguna de ellas; si una política no puede evaluarse, el acceso SHALL denegarse.

#### Scenario: Crear política
- **WHEN** un Owner crea una política de red `10.0.0.0/8` por UI o GraphQL
- **THEN** la política se guarda y puede asignarse a cuentas

#### Scenario: IP permitida
- **WHEN** una cuenta de servicio con la política `10.0.0.0/8` llama a la API pública desde `10.1.2.3`
- **THEN** el acceso se evalúa con RBAC y la respuesta es la habitual

#### Scenario: IP no permitida
- **WHEN** la misma cuenta llama desde `192.0.2.10`
- **THEN** la respuesta es 403 indicando que la política de red restringe el acceso

#### Scenario: Política global
- **WHEN** existe una política global de la organización y un miembro sin políticas propias accede desde una IP fuera de ella
- **THEN** el acceso se deniega

#### Scenario: Política malformada
- **WHEN** una política contiene una entrada que no es IP ni CIDR válido
- **THEN** esa entrada no concede acceso y la creación por UI/API se rechaza con error de validación

#### Scenario: Política heredada
- **WHEN** una cuenta de servicio con una política de red existente en la base de datos (p. ej. migrada desde Phase) llama a la API pública
- **THEN** la política se evalúa contra la IP de cliente en lugar de denegar siempre

#### Scenario: Sin políticas
- **WHEN** una cuenta sin políticas propias ni globales accede
- **THEN** el acceso se evalúa solo con RBAC

#### Scenario: Cabeceras de proxy no confiables
- **WHEN** una petición llega directamente al backend con `X-Forwarded-For: 10.1.2.3` desde una IP no configurada como proxy de confianza
- **THEN** la IP evaluada es la de la conexión, no la de la cabecera

#### Scenario: Operaciones GraphQL sin organisation_id
- **WHEN** un miembro al que una política excluye su IP consulta o modifica recursos de la organización por GraphQL con argumentos que no son `organisationId` (p. ej. `secrets(envId)`, `folders(envId)`, mutaciones por `id`/`ids` o listas de inputs)
- **THEN** la petición se deniega igual que con `organisationId`, y en operaciones masivas se comprueban todas las organizaciones referenciadas

#### Scenario: Entrada de X-Forwarded-For aportada por el cliente
- **WHEN** un proxy de confianza reenvía `X-Forwarded-For: 10.1.2.3, 198.51.100.7` sin `X-Real-IP`, donde `10.1.2.3` lo envió el cliente
- **THEN** la IP evaluada es `198.51.100.7` (la cadena se recorre de derecha a izquierda saltando proxies de confianza)

#### Scenario: Emisión de tokens con identidad externa
- **WHEN** una cuenta de servicio cuyas políticas excluyen la IP del cliente pide un token mediante una identidad externa (AWS IAM, Azure Entra)
- **THEN** la respuesta es 403 por política de red y no se contacta con el proveedor de identidad
