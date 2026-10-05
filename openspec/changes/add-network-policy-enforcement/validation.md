# Validación — add-network-policy-enforcement

Comprobaciones ejecutadas; datos sintéticos.

## Tests

| Comprobación | Resultado |
|---|---|
| Backend `pytest tests/` | 2531 passed (nuevo `tests/test_network_policies.py`: 35 tests de coincidencia IPv4/IPv6/mapeadas, entradas inválidas, globales, sin IP de cliente, validación en mutaciones; `tests/api/utils/access/test_ip.py` con suplantación de cabeceras y `TRUSTED_PROXY_CIDRS`) |
| Frontend `tsc --noEmit` / jest | 0 errores / 21 suites, 458 tests |
| `scripts/check-libreseal-guard.sh` | OK |

## Instancia local (clon limpio en `feat/network-policy-enforcement`, `docker compose up -d --build`)

IP de cliente vista por el servidor desde el host: `192.168.65.1` (Docker Desktop, a través de nginx).

| Escenario de la spec | Resultado |
|---|---|
| Crear política | `createNetworkAccessPolicy` OK; asignación a `agent-demo` OK; UI muestra "Create policy" sin insignia "not available"; Ajustes lista la función como disponible |
| Política malformada | `10.0.0.0/8, nope` rechazada: "Invalid IP address or CIDR range: nope" |
| IP permitida | Política `192.168.65.0/24` → API 200 |
| IP no permitida | Política `10.0.0.0/8` → 403 "a network access policy restricts access from your IP address" |
| Cabeceras falsas a través de nginx | `X-Real-IP`/`X-Forwarded-For: 10.1.2.3` → 403 (nginx sobrescribe `X-Real-IP`) |
| Sin políticas | Otra cuenta sin políticas → 200; tras desasignar → 200 |
| Política global | `10.0.0.0/8` global → cuenta de servicio 403 y Owner por GraphQL "Your IP address is not allowed to access homelab" |
| Recuperación ante bloqueo | `libreseal_clear_network_policies` lista y `--yes` borra; acceso restaurado (200) |
| Cabeceras no confiables directas al backend | Con `TRUSTED_PROXY_CIDRS=<IP de nginx>/32`, petición directa a `backend:8000` desde otro contenedor con `X-Real-IP: 10.1.2.3` y política `10.0.0.0/8` → 403; con la política ampliada a la red real del peer → 200 (se evalúa la IP de la conexión). `.env` restaurado después |

## IP real detrás de otro proxy (tarea 2.3)

Automático: `scripts/tests/test-nginx-real-ip.sh` (por defecto sin proxies de confianza, IPv4/CIDR/IPv6, cabecera de Cloudflare, entradas y cabeceras inválidas rechazadas sin tocar la config) → OK; `shellcheck` sobre el script y el test → sin avisos.

En vivo, con el host (`192.168.65.1`) haciendo de proxy exterior y una política en `agent-demo` que solo permite `203.0.113.9`:

| Escenario | Resultado |
|---|---|
| Sin `NGINX_REAL_IP_FROM`, cliente envía `X-Forwarded-For: 203.0.113.9` | 403 (se ignora; log de nginx `192.168.65.1`) |
| `NGINX_REAL_IP_FROM=192.168.65.1`, `XFF: 203.0.113.9` | `nginx -t` OK; 200 (log `203.0.113.9`) |
| Mismo proxy, `XFF: 198.51.100.1` | 403 |
| Mismo proxy, cliente antepone `XFF: 203.0.113.9, 198.51.100.1` | 403 (recursivo: cuenta la entrada añadida por el proxy de confianza) |
| `NGINX_REAL_IP_FROM='10.0.0.0/8;evil'` | nginx no arranca: "invalid NGINX_REAL_IP_FROM entry" |

Después se restauró la configuración por defecto (spoof → 403), se borró la política de prueba (→ 200).

## Revisión: GraphQL sin `organisation_id` (tarea 1.4)

Hallazgo de la revisión de código: el middleware GraphQL heredado solo aplicaba políticas cuando el resolver recibía `organisation_id`.

Reproducción en vivo antes del arreglo (sesión de Owner con `django.test.Client` dentro del contenedor, `REMOTE_ADDR=192.0.2.10`, política global `10.0.0.0/8`):

| Consulta | Antes | Después |
|---|---|---|
| `apps(organisationId)` | denegada | denegada |
| `secrets(envId)` | **200 con 11 secretos (cifrados)** | denegada "Your IP address is not allowed to access homelab" |
| `folders(envId)` | 200 | denegada |

Control positivo con la política ampliada a `192.0.2.0/24`: las tres consultas responden (2 apps, 11 secretos). Política de prueba borrada al terminar.

Automático: suite backend 2684 passed, 11 skipped (incluye el test de cobertura del esquema, 143 campos raíz, y tests de middleware para `envId`, `secretId`, `folderId`, `id`, `ids` mezclando organizaciones y listas de inputs). Comprobación negativa: quitando el alias `folder_id` el test de cobertura falla en `deleteSecretFolder`.

Regresión de UI: CRUD de secretos por la UI (Playwright, a través de nginx) → crear/editar/borrar OK, sin texto en claro en peticiones.
