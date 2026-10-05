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
