# Proposal

## Why

Las PR iniciales de LibreSeal se fusionaron sin que la integración continua se ejecutara nunca en el servidor ni en los skills. El workflow `LibreSeal CI` de `Dos2Locos/libreseal` está activo y es válido, pero GitHub tiene 0 ejecuciones registradas: los forks no ejecutan workflows hasta que alguien acepta el aviso de la pestaña Actions. `Dos2Locos/libreseal-skills` no tiene ningún workflow. Ahora que `main` es la rama de trabajo, cada cambio debe pasar por CI y no debe poder fusionarse con la CI en rojo.

## What Changes

- **Servidor (`libreseal`)**
  - Conseguir que `LibreSeal CI` se ejecute en `pull_request` y `push` a `main`.
  - Añadir `workflow_dispatch` para poder lanzarla a mano.
  - Corregir los fallos reales que aparezcan en su primera ejecución, ya que nunca ha corrido en GitHub.
- **Skills (`libreseal-skills`)**: workflow nuevo que valide sin red ni secretos:
  - `shellcheck` de los scripts;
  - frontmatter de cada `SKILL.md` (`name` igual al directorio, `description` presente);
  - sintaxis de las plantillas de nginx documentadas, con `nginx -t`;
  - que no se versionen ficheros `.env` ni tokens con formato de LibreSeal o Phase.
- **CLI (`libreseal-cli`)**: su CI ya se ejecuta y pasa; no se cambia.
- **Protección de `main` en los tres repositorios**:
  - solo se fusiona mediante PR;
  - los checks de CI son obligatorios y la rama debe estar al día;
  - sin force-push ni borrado.
  - Se aplica con un script versionado en `libreseal` para poder reproducirla.
  - No se exige aprobación de revisores, porque hay un solo mantenedor y eso bloquearía todos los merges; queda anotado como decisión revisable.
- **Documentación**: README de `libreseal` y de `libreseal-skills`, explicando qué valida la CI y que `main` está protegida.

**BREAKING (proceso)**: dejan de ser posibles los `push` directos a `main` y los merges con checks en rojo. No hay cambios funcionales del producto.

**Fuera de alcance**:
- publicar imágenes o releases (cambio aparte);
- CI de Kubernetes/Helm;
- aprobación obligatoria de revisores;
- reglas de organización de GitHub;
- cambios en el código del producto, salvo los arreglos mínimos que exija que la CI existente pase.

**Repositorios afectados**: `libreseal` (workflow, script de protección, README y los arreglos que pida la CI), `libreseal-skills` (workflow nuevo y README) y `libreseal-cli` (solo la protección de `main`, aplicada por API; sin commits).

**Código `ee/`**: ninguno. El workflow del servidor ya ejecuta `scripts/check-libreseal-guard.sh`, que falla si reaparece `ee/`. Este cambio hace que esa comprobación sea obligatoria antes de fusionar.

## Capabilities

### New Capabilities
- `continuous-integration`: qué valida automáticamente cada repositorio de LibreSeal, cuándo se ejecuta y qué condiciones debe cumplir un cambio para fusionarse en `main`.

### Modified Capabilities
_(ninguna)_

## Impact

- **GitHub (estado externo, no versionado)**:
  - aceptación de workflows en los forks `Dos2Locos/libreseal` y `Dos2Locos/libreseal-skills`;
  - reglas de protección de `main` en los tres repositorios, aplicadas con la cuenta `temperatio`, que es admin.
- **`libreseal`**:
  - `.github/workflows/main.yml` (`workflow_dispatch`);
  - nuevo `scripts/github/protect-main.sh`;
  - README;
  - posibles arreglos de dependencias, lint o build detectados por la primera ejecución.
- **`libreseal-skills`**:
  - nuevo `.github/workflows/ci.yml`;
  - script de validación en `scripts/`;
  - README.
- **Contribución**: todo cambio, incluidos los de los mantenedores, pasa por PR con CI en verde.
- **Coste**: los minutos de Actions son gratuitos en repositorios públicos.
