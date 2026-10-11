# Spec Delta

## ADDED Requirements

### Requirement: Enrutado interno aislado de redes compartidas
El nginx y el frontend de LibreSeal SHALL localizar el backend y el frontend por los nombres `libreseal-backend` y `libreseal-frontend`, definidos en la red interna del stack. Conectar el stack a una red compartida con servicios llamados `backend` o `frontend` SHALL NOT desviar ninguna petición a esos servicios.

#### Scenario: Red compartida con servicios homónimos
- **WHEN** con LibreSeal en marcha se crea una red Docker `shared-test` con dos contenedores de prueba con alias `backend` y `frontend` que responden siempre `IMPOSTOR`, se conecta `libreseal-nginx` a esa red y se ejecuta 20 veces `curl -sk https://localhost/service/health/` y `curl -sk https://localhost/login`
- **THEN** las 20 respuestas de salud contienen la versión de LibreSeal, las 20 de `/login` sirven la página de LibreSeal y ninguna contiene `IMPOSTOR`

#### Scenario: Llamadas del frontend al backend
- **WHEN** en esa misma situación se conecta también `libreseal-frontend` a `shared-test` y se inicia sesión en la UI y se lista una app
- **THEN** la sesión y el listado funcionan, y los contenedores de prueba no registran ninguna petición

#### Scenario: Guard ante nombres genéricos
- **WHEN** una PR cambia `nginx/default.conf` para que vuelva a usar `http://backend:8000`, o `docker-compose.yml` para que `BACKEND_API_BASE` vuelva a `http://backend:8000`
- **THEN** el check `guard` falla e indica el fichero y la línea

#### Scenario: Configuración antigua sigue funcionando
- **WHEN** una instancia actualizada a la versión con este cambio usa un `nginx/default.conf` anterior que apunta a `backend:8000` y `frontend:3000`, sin conectarse a redes compartidas
- **THEN** `curl -sk https://localhost/service/health/` devuelve la versión y la UI funciona
