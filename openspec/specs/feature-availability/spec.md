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
Mientras LibreSeal no disponga de verificador propio de políticas de red, SHALL impedir crear o asignar políticas de red, y SHALL denegar el acceso de una cuenta (usuario o cuenta de servicio) que tenga políticas aplicables existentes, en lugar de ignorarlas.

#### Scenario: Crear política
- **WHEN** un Owner intenta crear una política de red por UI o GraphQL
- **THEN** la operación se rechaza indicando que la función no está disponible

#### Scenario: Política heredada
- **WHEN** una cuenta de servicio con una política de red existente en la base de datos llama a la API pública
- **THEN** la respuesta es 403 y el error indica que las políticas de red no pueden verificarse

#### Scenario: Sin políticas
- **WHEN** una cuenta sin políticas de red llama a la API pública
- **THEN** el acceso se evalúa solo con RBAC
