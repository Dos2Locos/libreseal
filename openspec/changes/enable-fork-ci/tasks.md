# Tasks

## 1. CI del servidor en marcha

- [x] 1.1 Rama `ci/enable-fork-ci`. Añadir `workflow_dispatch` a `.github/workflows/main.yml`. Verificar con `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/main.yml'))"` y `scripts/check-libreseal-guard.sh`.
- [x] 1.2 Desbloquear los workflows del fork:
  - probar `gh api -X PUT repos/Dos2Locos/libreseal/actions/workflows/<id>/enable` y `gh workflow run "LibreSeal CI" --ref ci/enable-fork-ci`;
  - si `gh run list -R Dos2Locos/libreseal` sigue vacío, pedir al mantenedor que acepte el aviso en la pestaña Actions y repetir.
  - Verificar con una ejecución que aparece en `gh run list`.
- [x] 1.3 Abrir la PR de la rama contra `main`. Corregir los fallos que salgan en la primera ejecución con arreglos mínimos (dependencias, lint, build), sin desactivar jobs; si un arreglo cambia comportamiento del producto, parar y proponerlo aparte. Verificar:
  - `gh pr checks` muestra `guard`, `backend`, `frontend` y `compose-build` en verde;
  - cada arreglo reproducido antes en local con el mismo comando del workflow.
- [x] 1.4 Comprobar el escenario "Reaparece código ee/": en una rama desechable con un fichero `backend/ee/x.py`, `scripts/check-libreseal-guard.sh` falla en local y el check `guard` falla en una PR borrador. Cerrar la PR y borrar la rama.

## 2. CI de los skills

- [x] 2.1 [skills] Marcar con `# fragment` en la primera línea los bloques `nginx` que son fragmentos: líneas `ssl_certificate` de `docker-compose-deployment.md` y bloque `location` de `troubleshooting.md`. Verificar con `grep -n -A1 '```nginx' docker-compose/refs/*.md`.
- [x] 2.2 [skills] Crear `scripts/validate-skills.sh` (frontmatter, `shellcheck`, `nginx -t` con la imagen oficial fijada por digest, búsqueda de `.env` y tokens sin mostrar valores). Verificar en local:
  - pasa sobre el repositorio actual;
  - falla en cada caso de la spec: `name` cambiado en `docker-compose/SKILL.md`, directiva inválida en un bloque `nginx` y fichero temporal con `pss_service:v2:abc`;
  - la salida del caso del token no contiene el valor.
- [x] 2.3 [skills] Crear `.github/workflows/ci.yml`:
  - job `validate`, en `pull_request` y `push` a `main` y con `workflow_dispatch`;
  - `permissions: contents: read` y acciones fijadas por SHA.
  - Documentar en el README qué valida la CI y cómo ejecutarla en local.
  - Verificar con `shellcheck scripts/validate-skills.sh` y YAML válido.
- [x] 2.4 [skills] Desbloquear los workflows del fork como en 1.2, abrir la PR y conseguir el check `validate` en verde. Verificar con `gh pr checks -R Dos2Locos/libreseal-skills`.

## 3. Protección de main

- [x] 3.1 Crear `scripts/github/protect-main.sh` en `libreseal`:
  - modo comprobación por defecto, `--apply` y `--disable`;
  - checks obligatorios por repositorio según `design.md`;
  - `strict`, `enforce_admins`, PR obligatoria sin aprobaciones, y sin force-push ni borrado.
  - Verificar con `shellcheck` y ejecutándolo en modo comprobación contra los tres repositorios: debe informar de que la protección falta, sin cambiar nada.
- [x] 3.2 Contrastar los nombres de checks exigidos con ejecuciones reales: `gh pr checks` de las PR de 1.3 y 2.4, y la última ejecución de `main` de `libreseal-cli`. Ajustar el script si difieren. Verificar con una ejecución en modo comprobación sin avisos de checks desconocidos.
- [ ] 3.3 Documentar en el README de `libreseal` (sección Contributing) que `main` está protegida, qué checks exige cada repositorio y cómo reaplicar o retirar la protección. Fusionar las PR de 1.3 y 2.4 con la CI en verde. Verificar que `gh run list --branch main` muestra ejecuciones en verde de ambos repositorios tras el merge.

## 4. Aplicación y validación

- [ ] 4.1 Ejecutar `scripts/github/protect-main.sh --apply`. Verificar el escenario "Checks obligatorios configurados" con `gh api repos/Dos2Locos/<repo>/branches/main/protection` en los tres repositorios, y que una segunda ejecución en modo comprobación no informa de diferencias (idempotencia).
- [ ] 4.2 Validar los escenarios de protección:
  - `git push origin HEAD:main` con un commit de prueba es rechazado en los tres repositorios;
  - una PR de prueba en `libreseal-skills` con un `SKILL.md` inválido tiene `validate` en rojo y `gh pr merge` la rechaza.
  - Cerrar las PR y borrar las ramas de prueba.
- [ ] 4.3 Registrar en `validation.md` la salida de cada escenario: ejecuciones, checks y respuestas de la API. Ejecutar `openspec validate enable-fork-ci --strict`.
