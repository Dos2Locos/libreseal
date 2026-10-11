# Design

## Context

Estado observado el 2026-10-11 (motivación en `proposal.md`):

- **`nginx/default.conf`**
  - Usa `resolver 127.0.0.11` con `set $backend_upstream http://backend:8000` y `set $frontend_upstream http://frontend:3000`, de modo que resuelve los nombres en cada petición.
  - Se monta desde el host (`./nginx/default.conf`), así que no está dentro de la imagen.
  - Se distribuye en el clon y en el paquete de despliegue.
- **`docker-compose.yml`**
  - Todos los servicios están en la red `libreseal-net` y tienen `container_name: libreseal-*`.
  - El frontend recibe `BACKEND_API_BASE: "http://backend:8000"`.
  - El backend acepta `ALLOWED_HOSTS: "${HOST},backend"`; su comprobación de salud envía `Host: backend`.
  - nginx reenvía al backend la cabecera `Host` pública, no `backend`.
- **Docker** resuelve un nombre con los contenedores de todas las redes a las que está conectado quien pregunta. Si dos redes tienen un servicio `backend`, el resultado mezcla contenedores de proyectos distintos.
- **Dokploy**, sin despliegue aislado, conecta el servicio que lleva el dominio (aquí `nginx`) a `dokploy-network`, donde hay otros `backend` y `frontend`. El despliegue de LibreSeal usa ahora el modo aislado.

## Goals / Non-Goals

**Goals:**
- Que nginx y el frontend lleguen siempre a los servicios de su propio stack, aunque estén conectados a otras redes.
- Que ningún fichero existente deje de funcionar: ni los `nginx/default.conf` antiguos, ni los `.env` actuales, ni la comprobación de salud.

**Non-Goals:**
- Soportar dos instalaciones de LibreSeal en la misma red compartida. Hoy lo impiden los `container_name` fijos.
- Cambiar los nombres de servicio de Compose (`backend`, `frontend`, …) o los de PostgreSQL y Redis en el `.env`.

## Decisions

### 1. Alias de red únicos en `libreseal-net`
Cada servicio declara `networks: libreseal-net: aliases: [libreseal-<svc>]`. En el caso del backend, el alias va solo en `backend`, no en `migrations` ni en `worker`, que comparten imagen pero no atienden HTTP.

- El alias pertenece a la red interna del stack. Ningún otro proyecto lo tiene salvo otra instalación de LibreSeal, que está fuera de alcance.
- *Alternativa: usar el `container_name` (`libreseal-backend`, que ya es único por host).* Se descarta como mecanismo principal porque dejaría de funcionar si una plataforma reescribe o quita los `container_name`, como hacen algunas para evitar conflictos. El alias es explícito y no depende de eso. De paso, el nombre coincide con el del contenedor.
- *Alternativa: renombrar los servicios de Compose.* Se descarta porque rompería `docker compose exec backend …`, los scripts de copia, la documentación y los `nginx/default.conf` antiguos.

### 2. Upstreams de nginx
`$backend_upstream` pasa a `http://libreseal-backend:8000` y `$frontend_upstream` a `http://libreseal-frontend:3000`. Se mantiene la resolución en cada petición (`resolver 127.0.0.11`), que evita los 502 tras recrear contenedores. Los comentarios del fichero explican el motivo.

### 3. Frontend y `ALLOWED_HOSTS`
`BACKEND_API_BASE` pasa a `http://libreseal-backend:8000`. `ALLOWED_HOSTS` queda como `"${HOST},backend,libreseal-backend"`: se añade el nombre nuevo porque Django valida el `Host` de las llamadas del frontend, y se conserva `backend` para la comprobación de salud y para configuraciones antiguas. Es un nombre interno sin puerto publicado, así que no amplía lo que se puede alcanzar desde fuera.

### 4. Guard
`check-libreseal-guard.sh` busca `//backend:` y `//frontend:` en `nginx/default.conf` y `docker-compose.yml`, y falla mostrando el fichero y la línea. Los ficheros de desarrollo, staging y Tailscale, heredados de Phase, quedan fuera de la comprobación.

### 5. Test de red compartida
`scripts/tests/test-shared-network.sh` comprueba un stack ya levantado (sin compilar ni levantar nada) y deja todo como estaba al terminar:
1. Crea una red temporal con dos impostores que responden `IMPOSTOR` y tienen alias `backend` y `frontend`. Usan una imagen mínima fijada por digest.
2. Conecta nginx y el frontend a esa red.
3. Hace 20 peticiones a `/service/health/` y a `/login`, y falla si alguna respuesta contiene `IMPOSTOR` o no es de LibreSeal.
4. Desconecta los servicios y borra la red y los impostores.

El job `compose-build` solo construye imágenes, así que el test se ejecuta en la validación local y se documenta. Meterlo en CI exigiría levantar el stack completo en cada PR.

### 6. Versión y despliegue
- Se publica `v0.1.1` con el proceso de `release-publishing`: `set-version.sh`, PR y tag.
- En Dokploy se cambia `LIBRESEAL_VERSION=0.1.1` y se redespliega. Dokploy toma el `nginx/default.conf` del repositorio, así que el despliegue recibe la configuración nueva.
- El modo aislado se mantiene.

## Risks / Trade-offs

- **[Riesgo] Un usuario mantiene su `nginx/default.conf` personalizado (por ejemplo, para Let's Encrypt) con los nombres antiguos.**
  → Sigue funcionando, pero sin la protección. Las notas de la release y el skill `docker-compose` le indican cómo cambiar las dos líneas `set $…_upstream`.
- **[Riesgo] Las plataformas que ignoran `aliases`.**
  → El `container_name` coincide con el alias y sirve de respaldo. La validación incluye la ejecución en Dokploy.
- **[Trade-off] El test de red compartida no corre en CI.** Se acepta porque es una regresión de configuración que ya cubre el guard; el test de comportamiento se ejecuta en cada validación de release.

## Migration Plan

1. Fusionar los cambios de `libreseal` y, después, los de `libreseal-skills`.
2. Publicar `v0.1.1`.
3. En Dokploy, poner `LIBRESEAL_VERSION=0.1.1` y redesplegar.
4. Las instalaciones con Compose actualizan con el procedimiento habitual: checkout del tag o paquete nuevo, `docker compose pull` y `docker compose up -d`.

**Vuelta atrás:** usar la configuración anterior o fijar `LIBRESEAL_VERSION=0.1.0`. La configuración antigua sigue siendo válida con las imágenes nuevas.
