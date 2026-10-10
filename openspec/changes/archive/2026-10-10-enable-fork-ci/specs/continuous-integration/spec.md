# Spec Delta

## Purpose
Define qué comprueba automáticamente la integración continua de cada repositorio de LibreSeal (servidor, CLI y skills), cuándo se ejecuta y qué condiciones debe cumplir un cambio para fusionarse en `main`.

## ADDED Requirements

### Requirement: CI del servidor en cada cambio
El repositorio `Dos2Locos/libreseal` SHALL ejecutar en GitHub Actions el workflow `LibreSeal CI` en cada `pull_request` contra `main`, en cada `push` a `main` y bajo demanda (`workflow_dispatch`).

El workflow SHALL incluir:
- la comprobación de invariantes (`scripts/check-libreseal-guard.sh`) y los tests de los scripts de despliegue;
- los tests del backend;
- la comprobación de tipos, los tests y el lint del frontend;
- la construcción de las imágenes con `docker compose build`.

No SHALL publicar imágenes ni artefactos en ningún registro.

#### Scenario: PR contra main
- **WHEN** se abre una PR contra `main` en `Dos2Locos/libreseal`
- **THEN** `gh pr checks <n> -R Dos2Locos/libreseal` muestra los checks `guard`, `backend`, `frontend` y `compose-build` ejecutados

#### Scenario: Push a main
- **WHEN** se fusiona una PR en `main`
- **THEN** `gh run list -R Dos2Locos/libreseal --branch main --workflow "LibreSeal CI"` muestra una ejecución para ese commit con conclusión `success`

#### Scenario: Ejecución manual
- **WHEN** un mantenedor ejecuta `gh workflow run "LibreSeal CI" -R Dos2Locos/libreseal --ref main`
- **THEN** se crea una ejecución del workflow sobre `main`

#### Scenario: Reaparece código ee/
- **WHEN** una PR añade un fichero bajo un directorio `ee/`
- **THEN** el check `guard` falla

#### Scenario: Sin publicación
- **WHEN** se ejecuta el workflow en `main`
- **THEN** ningún paso hace `docker push`, `docker login` ni publica releases, y los permisos del token del workflow se limitan a `contents: read`

### Requirement: CI de los skills
El repositorio `Dos2Locos/libreseal-skills` SHALL ejecutar en GitHub Actions un workflow en cada `pull_request` contra `main`, en cada `push` a `main` y bajo demanda. Sin acceso a secretos ni a un servidor LibreSeal, SHALL validar que:
- los scripts de shell superan `shellcheck`;
- cada `SKILL.md` tiene frontmatter con `name` igual a su directorio y una `description` no vacía;
- cada bloque `nginx` de la documentación supera `nginx -t`;
- el repositorio no contiene ficheros `.env` ni cadenas con formato de token de LibreSeal o Phase (`pss_service:`, `pss_user:`).

#### Scenario: Skill con frontmatter incorrecto
- **WHEN** una PR cambia el `name` de `docker-compose/SKILL.md` a un valor distinto de `docker-compose`
- **THEN** el check de validación de skills falla e indica el fichero

#### Scenario: Plantilla de nginx inválida
- **WHEN** una PR introduce en un bloque `nginx` de `docker-compose/refs/` una directiva inexistente
- **THEN** el check falla mostrando la salida de `nginx -t`

#### Scenario: Token versionado
- **WHEN** una PR añade un fichero que contiene `pss_service:v2:`
- **THEN** el check falla sin imprimir el valor completo

#### Scenario: Repositorio válido
- **WHEN** se ejecuta el workflow sobre `main` actual
- **THEN** concluye con `success`

### Requirement: main protegida en los repositorios de LibreSeal
La rama `main` de `Dos2Locos/libreseal`, `Dos2Locos/libreseal-cli` y `Dos2Locos/libreseal-skills` SHALL aceptar cambios solo mediante PR, cuyos checks de CI obligatorios hayan concluido con éxito y estén al día con `main`. SHALL rechazar los `push` directos, los force-push y el borrado de la rama. La configuración SHALL poder reaplicarse con un script versionado en `Dos2Locos/libreseal`.

#### Scenario: Push directo rechazado
- **WHEN** un mantenedor ejecuta `git push origin HEAD:main` con un commit nuevo en cualquiera de los tres repositorios
- **THEN** GitHub rechaza el push indicando que la rama está protegida

#### Scenario: Merge con CI en rojo rechazado
- **WHEN** se intenta `gh pr merge <n> --merge` sobre una PR cuyo check obligatorio ha fallado
- **THEN** GitHub rechaza el merge

#### Scenario: Checks obligatorios configurados
- **WHEN** se consulta `gh api repos/Dos2Locos/<repo>/branches/main/protection`
- **THEN** la respuesta lista como checks obligatorios los jobs de CI de ese repositorio y `allow_force_pushes` y `allow_deletions` están desactivados

#### Scenario: Reaplicar la protección
- **WHEN** un admin ejecuta el script de protección versionado en `libreseal`
- **THEN** la protección de los tres repositorios queda igual a la documentada, sin cambios si ya lo estaba
