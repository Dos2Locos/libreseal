# feature-availability Specification

## Purpose
Determina qué funciones ofrece una instancia LibreSeal sin planes comerciales, cuotas, licencias ni facturación, y cómo se comportan las funciones no disponibles y los controles de seguridad sin verificador.

## Requirements

### Requirement: Sin cuotas comerciales
Una instancia LibreSeal SHALL permitir crear apps, entornos (incluidos personalizados), miembros, invitaciones y cuentas de servicio sin límites derivados de planes, asientos o licencias. Solo SHALL aplicar los permisos RBAC del usuario.

#### Scenario: Más de tres entornos
- **WHEN** un usuario con permiso de crear entornos crea un cuarto entorno personalizado en una app mediante la UI o `POST /service/public/v1/environments/`
- **THEN** el entorno se crea y no aparece ningún mensaje de plan, upgrade o límite

#### Scenario: Muchas cuentas de servicio y miembros
- **WHEN** un administrador crea seis cuentas de servicio e invita a seis miembros en una organización nueva
- **THEN** todas las operaciones se completan sin error de cuota

### Requirement: Funciones núcleo habilitadas
Roles personalizados, equipos y entornos personalizados SHALL estar disponibles en toda organización LibreSeal, sujetos únicamente a RBAC.

#### Scenario: Crear rol personalizado
- **WHEN** un Owner crea un rol personalizado desde "Access → Roles" o con la mutación GraphQL `createCustomRole`
- **THEN** el rol se crea sin error "not available on your organisation's plan"

#### Scenario: Crear equipo
- **WHEN** un Owner crea un equipo desde "Access → Teams"
- **THEN** el equipo se crea y no se muestra diálogo de upgrade

### Requirement: Sin facturación, licencias ni upsell
LibreSeal SHALL NOT mostrar planes, precios, diálogos de upgrade, formularios de solicitud de upgrade, pantallas de checkout ni activación de licencias, y SHALL NOT exponer el webhook de Stripe.

#### Scenario: Ajustes de organización
- **WHEN** un Owner abre los ajustes de la organización
- **THEN** no aparecen secciones de plan, facturación, licencia ni botones de upgrade

#### Scenario: Webhook retirado
- **WHEN** se envía `POST /service/stripe/webhook/`
- **THEN** la respuesta es 404

### Requirement: Funciones no disponibles explícitas
Las funciones cuya implementación upstream solo existe bajo licencia Enterprise (dynamic secrets, rotación, log streams, SCIM, SSO OIDC empresarial) SHALL mostrarse como no disponibles en LibreSeal y sus API SHALL responder con un error explícito, sin ofrecer compra ni upgrade.

#### Scenario: UI de función no disponible
- **WHEN** un usuario abre "Integrations → Log streams" o el menú de crear secreto dinámico/rotatorio
- **THEN** la UI indica "No disponible en LibreSeal" sin enlaces de compra

#### Scenario: API de dynamic secrets
- **WHEN** un cliente llama a `GET /service/public/v1/secrets/dynamic/` con un token válido
- **THEN** recibe 404 o 501 con un mensaje que indica que la función no está disponible en LibreSeal

#### Scenario: Lectura de secretos sin dynamic secrets
- **WHEN** un cliente lee `GET /service/public/v1/secrets/?app_id=<id>&env=<env>`
- **THEN** recibe los secretos estáticos con el mismo formato que upstream

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
