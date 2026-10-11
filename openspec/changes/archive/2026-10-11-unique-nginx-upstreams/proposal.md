# Proposal

## Why

Dentro del stack de Compose, el nginx de LibreSeal y el frontend localizan el backend y el frontend por los nombres genéricos de servicio `backend` y `frontend`. El nginx los resuelve en cada petición con el DNS de Docker. Cuando nginx se conecta también a una red compartida con otros proyectos (en Dokploy, `dokploy-network`, para que Traefik lo alcance), Docker devuelve los contenedores de cualquier proyecto que tenga un servicio con ese nombre. El 2026-10-11, en `libreseal.dos2locos.es`, las peticiones a `/service/` acabaron en los backends de `amano` y `rbm`, que respondieron 400.

Se resolvió activando el despliegue aislado de Dokploy, pero el fallo es del producto. En otra plataforma, o sin esa opción, LibreSeal podría enviar peticiones (con cookies de sesión y cabeceras de autenticación) a un servicio ajeno.

## What Changes

- **libreseal**: los servicios propios del stack obtienen alias únicos en su red interna `libreseal-net`: `libreseal-backend` y `libreseal-frontend`.
- **libreseal**: `nginx/default.conf` envía `/service/` a `libreseal-backend:8000` y `/` a `libreseal-frontend:3000`.
- **libreseal**: el frontend llama al backend por `http://libreseal-backend:8000`, y `ALLOWED_HOSTS` acepta ese nombre. Se mantiene `backend`, que usa la comprobación de salud interna.
- **libreseal**: `scripts/check-libreseal-guard.sh` falla si `nginx/default.conf` o `docker-compose.yml` vuelven a usar `backend` o `frontend` como host entre servicios.
- **libreseal**: se publica la versión `v0.1.1`, para que el paquete de despliegue lleve la configuración corregida. Después se actualiza el despliegue de Dokploy.
- **libreseal-skills**: el skill `docker-compose` y sus referencias muestran el bloque de nginx con los nombres nuevos.

No hay cambios incompatibles. Las instalaciones existentes que actualicen sus ficheros (checkout o paquete nuevos) pasan a usar los nombres nuevos. Las que mantengan su `nginx/default.conf` antiguo siguen funcionando igual que hoy, porque los nombres de servicio `backend` y `frontend` siguen existiendo.

Fuera de alcance:
- `DATABASE_HOST=postgres` y `REDIS_HOST=redis` del `.env`. Solo los usa el backend, que no se conecta a redes compartidas. Cambiarlos obligaría a editar el `.env` de cada instalación.
- `dev-docker-compose.yml`, `staging-docker-compose.yml`, `tailscale-docker-compose.yml` y `tailscale/nginx.conf`, restos del proyecto original sin soporte en LibreSeal.
- Las guías `k8s`, `eks` y `aks` de `libreseal-skills`, no adaptadas.
- Desactivar el despliegue aislado en Dokploy: sigue siendo una defensa adicional.

## Capabilities

### New Capabilities
<!-- Ninguna -->

### Modified Capabilities
- `self-hosted-deployment`: nuevo requisito que exige que el enrutado interno entre servicios de LibreSeal no dependa de nombres que puedan existir en otras redes a las que se conecte el stack.

## Impact

- **libreseal**:
  - `nginx/default.conf` y `docker-compose.yml` (alias de red, `BACKEND_API_BASE` y `ALLOWED_HOSTS`);
  - `scripts/check-libreseal-guard.sh` y un test nuevo con una red compartida simulada;
  - `README.md`, si menciona los nombres;
  - la versión `0.1.1`, con `scripts/set-version.sh`.
- **libreseal-skills**: `docker-compose/SKILL.md` y `docker-compose/refs/docker-compose-deployment.md`.
- **libreseal-cli**: no cambia.
- **Despliegue**: el compose `libreseal` de Dokploy pasa a `LIBRESEAL_VERSION=0.1.1` y se redespliega.
- **Código `ee/`**: ninguna dependencia afectada; el cambio solo toca configuración de Compose y nginx, scripts y documentación.
- **Seguridad**: no se debilita ningún control. Se evita que las peticiones de los usuarios, con sus cookies y tokens, puedan llegar a servicios de otros proyectos.
