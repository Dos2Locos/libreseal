# Tasks

`main` está protegida: cada repositorio usa su propia rama y PR, y la PR solo se fusiona con los checks en verde. Antes de fusionar, crear tags o tocar Dokploy se pide confirmación expresa al usuario.

## 1. Nombres únicos en el stack

- [x] 1.1 Rama `fix/unique-nginx-upstreams` en `libreseal`. En `docker-compose.yml`:
  - alias `libreseal-backend` en el servicio `backend` y `libreseal-frontend` en `frontend`, dentro de `libreseal-net`;
  - `BACKEND_API_BASE: "http://libreseal-backend:8000"`;
  - `ALLOWED_HOSTS: "${HOST},backend,libreseal-backend"`.

  Verificar que `docker compose config` y `docker compose -f docker-compose.yml -f docker-compose.build.yml config` son válidos y muestran los alias.
- [x] 1.2 Cambiar `nginx/default.conf` a `http://libreseal-backend:8000` y `http://libreseal-frontend:3000`, con un comentario que explique el motivo. Verificar con `nginx -t` en la imagen `ghcr.io/dos2locos/libreseal-nginx:0.1.0`, montando el fichero y con resolución de nombres disponible, por ejemplo dentro del stack de prueba de 1.4.
- [x] 1.3 Ampliar `scripts/check-libreseal-guard.sh` para que falle si `nginx/default.conf` o `docker-compose.yml` contienen `//backend:` o `//frontend:`, mostrando el fichero y la línea. Verificar:
  - el guard pasa en el árbol;
  - falla en una copia temporal con `http://backend:8000` en cada uno de los dos ficheros (escenario "Guard ante nombres genéricos").
- [x] 1.4 Crear `scripts/tests/test-shared-network.sh` según la decisión 5 de `design.md` (impostores con imagen fijada por digest, 20 peticiones, limpieza con `trap`) y documentarlo en el README, en la sección de contribución. Verificar con `shellcheck` y ejecutándolo contra un stack local levantado con el override de compilación (proyecto aislado en 8080/8443):
  - pasa con los cambios de 1.1 y 1.2;
  - falla con el `nginx/default.conf` anterior, lo que demuestra que el test detecta el problema;
  - al terminar no quedan redes ni contenedores de prueba.

## 2. Validación local

- [x] 2.1 Escenario "Llamadas del frontend al backend": con el stack de 1.4 y nginx y el frontend conectados a la red de impostores, iniciar sesión con Playwright y listar una app. Verificar que funciona y que los registros de los impostores no muestran ninguna petición.
- [x] 2.2 Escenario "Configuración antigua sigue funcionando": en el mismo stack, sin red compartida, montar el `nginx/default.conf` de `v0.1.0`. Verificar que `/service/health/` responde y que la UI carga.
- [x] 2.3 Abrir la PR de `libreseal`. Verificar que `guard`, `backend`, `frontend` y `compose-build` están en verde.

## 3. Skills

- [x] 3.1 [skills] Rama `docs/unique-nginx-upstreams`:
  - actualizar en `docker-compose/refs/docker-compose-deployment.md` el diagrama y el bloque de nginx con los nombres nuevos;
  - cambiar en `docker-compose/SKILL.md` el principio "Preserve nginx routing";
  - añadir a `refs/troubleshooting.md` cómo migrar un `default.conf` personalizado (las dos líneas `set $…_upstream`).

  Verificar que `scripts/validate-skills.sh` pasa, incluido `nginx -t`, y abrir la PR con `validate` en verde.

## 4. Release y despliegue

- [x] 4.1 Con confirmación del usuario, fusionar las PRs de 2.3 y 3.1. Después, PR con `scripts/set-version.sh 0.1.1`, fusionarla y empujar el tag `v0.1.1`. Verificar:
  - `LibreSeal Release` termina en verde;
  - el paquete `libreseal-deploy-0.1.1.tar.gz` contiene el `nginx/default.conf` nuevo;
  - `cosign verify` es correcto en las tres imágenes `0.1.1`;
  - tras revisar el borrador, la release queda publicada.
- [x] 4.2 Con confirmación del usuario, poner `LIBRESEAL_VERSION=0.1.1` en el compose `libreseal` de Dokploy y redesplegar. Verificar:
  - `https://libreseal.dos2locos.es/service/health/` devuelve `v0.1.1`;
  - el login carga;
  - nginx usa los nombres nuevos (`docker exec libreseal-nginx grep upstream /etc/nginx/conf.d/default.conf`);
  - el registro con un dominio fuera de la lista sigue devolviendo 403.
- [x] 4.3 Escribir `validation.md` con los comandos ejecutados y sus resultados, y con cualquier comprobación no ejecutada y su motivo. Verificar con `openspec validate unique-nginx-upstreams --strict`.

## Workflow follow-up

- Archivar con `/opsx:archive unique-nginx-upstreams` en una rama con su PR.
