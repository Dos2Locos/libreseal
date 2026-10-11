# Validation — unique-nginx-upstreams

Registro de las comprobaciones ejecutadas el 2026-10-11. Solo se anota lo que se ha ejecutado de verdad, y los secretos usados son sintéticos.

**Versiones verificadas:**
- `libreseal`: `d22169f4`, tag `v0.1.1`.
- `libreseal-skills`: PR #5 fusionada.

## Entorno local

macOS arm64 con Docker 29.8.2. Para el stack de prueba se usaron las imágenes publicadas `0.1.0` con el `docker-compose.yml` y el `nginx/default.conf` del árbol nuevo, en los puertos 8080/8443 (el stack `tienda` ocupa 80/443). Es una desviación de la tarea 1.4, que pedía el override de compilación: este cambio no toca el código del backend ni del frontend, solo la configuración que se probó.

## Resultados

| Tarea | Comprobación | Resultado |
|---|---|---|
| 1.1 | `docker compose config` y la configuración con el override de compilación | Ambas válidas, con los alias `libreseal-backend` y `libreseal-frontend`. `BACKEND_API_BASE=http://libreseal-backend:8000`; `ALLOWED_HOSTS=${HOST},backend,libreseal-backend` |
| 1.2 | `nginx -t` en el stack (`libreseal-nginx:0.1.0` con el `default.conf` nuevo) | `syntax is ok` / `test is successful` |
| 1.3 | Guard con el árbol actual, con `http://backend:8000` en `nginx/default.conf` y en `BACKEND_API_BASE` | `OK`. Los dos casos fallan con código 1 y señalan `nginx/default.conf:16` (y `:34`) y `docker-compose.yml:50` |
| 1.4 | `shellcheck` 0.10.0; `scripts/tests/test-shared-network.sh https://localhost:8443` | `shellcheck` limpio. Con la configuración nueva: `20 health + 20 login requests stayed on LibreSeal; impostors untouched`, código 0, sin redes ni contenedores sobrantes. Con el `default.conf` de `v0.1.0`: `FAIL: health request 1 reached the impostor`, código 1 |
| 2.1 | `ATTACH_FRONTEND=1 KEEP_ATTACHED=1` y Playwright con los impostores conectados | El frontend queda en la red de prueba. Registro, onboarding, creación de la app `demo`, inicio de sesión (→ `/homelab`) y listado de apps correctos, sin `IMPOSTOR` en la página. Los impostores solo registran el control positivo; código 0 |
| 2.2 | `default.conf` de `v0.1.0` sin red compartida | Health `v0.1.0` 5/5; `/login` con título `Log in \| LibreSeal`; inicio de sesión y listado de apps correctos |
| 2.3 / 3.1 | libreseal#12 y libreseal-skills#5 | Checks `guard`, `backend`, `frontend`, `compose-build` y `validate` en verde. `validate-skills.sh` pasa, incluido `nginx -t` del bloque completo |
| 4.1 | #12, #5 y #13 (`set-version.sh 0.1.1`) fusionadas; tag `v0.1.1` → run `38143167783` | `success`. `shasum -c` del paquete OK; el `nginx/default.conf` del paquete usa `libreseal-backend:8000` y `libreseal-frontend:3000`; el compose tiene los 2 alias y `LIBRESEAL_VERSION:-0.1.1`. `cosign verify` correcto en las 3 imágenes. Release publicada como *Latest*, con una nota para quien haya personalizado `default.conf` |
| 4.2 | Dokploy: `LIBRESEAL_VERSION=0.1.1` (solo esa línea del entorno) y `compose.deploy` | Despliegue `done`. `/service/health/` → `v0.1.1` 5/5; login de LibreSeal. Registro con `probe@example.com` → 403 (la lista de dominios se mantiene). nginx usa `libreseal-backend` y `libreseal-frontend`; el backend tiene el alias `libreseal-backend`; el frontend usa `BACKEND_API_BASE=http://libreseal-backend:8000`. PostgreSQL y Redis no se recrearon, así que los datos se conservan. El despliegue aislado sigue activo |

## No ejecutado

- No se ha probado en Dokploy sin el despliegue aislado: se mantiene activo como defensa adicional, y el comportamiento en una red compartida ya está cubierto por el test local (1.4 y 2.1).
- El test de red compartida no corre en CI (decisión 5 de `design.md`). El guard sí, en cada PR.
