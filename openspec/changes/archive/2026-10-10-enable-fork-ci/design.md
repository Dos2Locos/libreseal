# Design

## Context

Estado observado el 2026-10-06 (ver `proposal.md` para la motivación):

- **Servidor (`Dos2Locos/libreseal`)**
  - `.github/workflows/main.yml` (`LibreSeal CI`) aparece como `active`.
  - Se dispara con `pull_request` y `push` a `main`, pero `GET /actions/runs` devuelve `total_count: 0`, incluido el `push` del merge de las PR #1 y #2.
  - Los permisos de Actions están habilitados (`enabled=true`, `allowed_actions=all`).
  - Las acciones fijadas por SHA existen y coinciden con las últimas releases: `checkout` v7.0.1, `setup-python` v7.0.0 y `setup-node` v7.0.0.
  - El síntoma coincide con el bloqueo de workflows en forks, que solo se levanta aceptando el aviso de la pestaña Actions.
- **CLI (`Dos2Locos/libreseal-cli`)**
  - Su CI (`Test & Build`, que llama a `Test and Vet`) se ejecuta y pasa en Ubuntu, macOS, Windows e `install-from-source`.
  - Usa etiquetas (`@v7`) en vez de SHAs.
- **Skills (`Dos2Locos/libreseal-skills`)**
  - No hay `.github/`.
  - El repositorio contiene:
    - cinco `SKILL.md`, cuatro de ellos con `description: |` multilínea;
    - un script, `libreseal-usage/examples/agent-demo.sh`;
    - tres bloques `nginx` en `docker-compose/refs/`.
  - La plantilla de Let's Encrypt incluye `/etc/nginx/real-ip.conf` y certificados que solo existen en la imagen de nginx de LibreSeal.
- **Ramas y permisos**
  - Ninguna `main` está protegida y no hay rulesets.
  - La cuenta `temperatio` es admin de los tres repositorios.
  - Los repositorios son públicos (plan free), así que la protección de ramas está disponible.

## Goals / Non-Goals

**Goals:**
- Que la CI se ejecute de verdad y en verde en los tres repositorios.
- Que fusionar en `main` exija esa CI en verde.
- Que la configuración de GitHub sea reproducible y revisable desde el repositorio.

**Non-Goals:**
- Unificar la CLI con SHAs fijados. Se recomienda, pero en otro cambio.
- Caché o matrices nuevas en el servidor.
- Rulesets a nivel de organización.
- Validar en CI la semántica de los skills contra un servidor real. Requeriría desplegar LibreSeal en cada ejecución; queda para cuando haya imágenes publicadas.

## Decisions

1. **Desbloquear los workflows del fork: primero por API, después a mano**
   - Primero se prueba `gh api -X PUT repos/Dos2Locos/libreseal/actions/workflows/<id>/enable` seguido de `gh workflow run` (tras añadir `workflow_dispatch`).
   - Si GitHub sigue sin crear ejecuciones, es el consentimiento de fork que solo existe en la UI. La tarea pasa al mantenedor: Actions → "I understand my workflows, go ahead and enable them". Después se comprueba con `gh run list`.
   - Alternativa descartada: recrear los repositorios como no-fork. Rompería la relación visible con upstream, que el proyecto quiere conservar.

2. **`workflow_dispatch` en el servidor**: permite verificar sin crear commits vacíos y sirve como señal inequívoca de que el bloqueo se ha levantado.

3. **Primera ejecución del servidor como fuente de tareas**
   - El workflow no ha corrido nunca, así que es probable que aparezcan fallos reales: `pip` con `constraints.txt`, `yarn lint`, tiempo de `compose-build`.
   - Se corrigen en la propia rama del cambio con el mínimo necesario. Si algún arreglo cambia comportamiento del producto o es grande, se para y se propone aparte.
   - No se desactiva ningún job para conseguir el verde.

4. **Validación de skills con un script propio**, `scripts/validate-skills.sh`, ejecutado igual en local y en CI, en lugar de encadenar acciones de terceros:
   - **Frontmatter**: se lee con Python, ya disponible en el runner, para tratar bien el `description: |` multilínea.
   - **`shellcheck`**: el preinstalado en `ubuntu-latest`.
   - **nginx**: se extraen los bloques ```` ```nginx ```` de `refs/*.md` y se valida cada uno con `nginx -t` en la imagen oficial `nginx` fijada por digest.
     - Para no depender de la imagen de LibreSeal, el script genera un `real-ip.conf` vacío y un certificado autofirmado temporal en las rutas que usan las plantillas.
     - Los bloques que son fragmentos (por ejemplo solo las líneas `ssl_certificate`) se marcan con un comentario `# fragment` en la primera línea y se omiten.
     - Alternativa descartada: construir la imagen de nginx de LibreSeal clonando el servidor. Acopla los dos repositorios y alarga la CI.
   - **Búsqueda de tokens y `.env`**: `git ls-files` más `grep -E 'pss_(service|user):v?[0-9]*:'`. Si hay coincidencia, se muestran solo el fichero y la línea, nunca el valor. Se descarta gitleaks por evitar otra dependencia externa para una regla de una línea.

5. **Protección de ramas clásica** (`PUT /repos/{repo}/branches/main/protection`), aplicada por `scripts/github/protect-main.sh` en `libreseal`. Se elige frente a los rulesets porque se lee y verifica con un único endpoint, y es lo que comprueba el escenario de la spec.
   - **Checks obligatorios por repositorio**:
     - `libreseal`: `guard`, `backend`, `frontend`, `compose-build`.
     - `libreseal-skills`: `validate`.
     - `libreseal-cli`: `test / Go Test & Vet (ubuntu-latest)`, `(macos-latest)`, `(windows-latest)` e `install-from-source`.
     - Los nombres se toman de ejecuciones reales (`gh pr checks`), no de los ficheros.
   - **Ajustes de la regla**:
     - `strict: true` (la rama debe estar al día con `main`);
     - `enforce_admins: true`, para que los mantenedores y los agentes que usan `temperatio` tampoco hagan `push` directo;
     - `required_pull_request_reviews` sin aprobaciones obligatorias (`required_approving_review_count: 0`), para forzar PR sin bloquear a un solo mantenedor;
     - `allow_force_pushes: false` y `allow_deletions: false`.
   - **El script**:
     - es idempotente;
     - por defecto muestra la diferencia entre la protección actual y la deseada; con `--apply`, la aplica;
     - usa el `gh` autenticado del operador y no guarda tokens.

6. **Orden de aplicación**: la protección se aplica cuando cada repositorio tiene al menos una ejecución en verde de los checks que se van a exigir. Si se exige un check que nunca ha corrido, ninguna PR podría fusionarse.

## Risks / Trade-offs

- [El consentimiento del fork no se puede dar por API] → la tarea queda asignada al mantenedor con instrucciones exactas. El resto del cambio no avanza hasta comprobar una ejecución real.
- [Con `enforce_admins`, un fallo de CI ajeno al código (caída de GitHub o de un registro) bloquea los merges] → se acepta. Un admin puede desactivar temporalmente la protección con el mismo script (`--disable`), lo que deja rastro en el log de auditoría de GitHub.
- [`compose-build` tarda bastante (construye backend y frontend)] → se acepta. Es el check que garantiza que la instalación documentada funciona.
- [Los nombres de checks de matriz (CLI) cambian si se renombra el job] → el script falla en modo comprobación si un check exigido no aparece en la última ejecución de `main`, para detectarlo.
- [El grep de tokens puede dar falsos positivos en documentación que muestra el prefijo (`pss_service:v2:…`)] → la regla exige caracteres después del prefijo y los ejemplos se escriben con `…` o `<token>`. Si hiciera falta una excepción, se haría con una lista explícita en el script.

## Migration Plan

1. Rama `ci/enable-fork-ci` en `libreseal` y en `libreseal-skills`, con los workflows y scripts.
2. Desbloquear Actions en los forks (API o paso manual del mantenedor). Ejecutar CI en las ramas y corregir hasta tener verde.
3. Fusionar las PR. Hasta ese momento no hay protección, así que se fusionan con CI en verde comprobada a mano.
4. Ejecutar `protect-main.sh` en modo comprobación y después con `--apply`. Verificar los escenarios: `push` directo rechazado y PR con check en rojo no fusionable.

**Rollback**: `scripts/github/protect-main.sh --disable` retira la protección; los workflows se pueden desactivar con `gh workflow disable`.
