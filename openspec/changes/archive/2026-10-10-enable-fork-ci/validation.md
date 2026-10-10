# Validación de enable-fork-ci

Ejecutado el 2026-10-06 con la cuenta `temperatio` (admin de los tres repositorios).

## CI del servidor (`Dos2Locos/libreseal`)

| Escenario | Resultado |
|---|---|
| Estado inicial | `GET /actions/runs` → `total_count: 0`: el workflow nunca se había ejecutado, ni siquiera en el `push` del merge de las PR #1 y #2 |
| Desbloqueo | `PUT /actions/workflows/375848977/enable` (código 0) seguido de `gh workflow run "LibreSeal CI" --ref ci/enable-fork-ci` creó la ejecución 37531697811. No hizo falta aceptar el aviso en la pestaña Actions |
| Ejecución manual | `workflow_dispatch` 37531697811: `success` |
| PR contra main | PR #3: `guard`, `backend`, `frontend` y `compose-build` en `pass` en todos sus commits. La primera ejecución pasó sin arreglos |
| Push a main | Tras fusionar la PR #3, ejecución `push` en `main` sobre `059cc394`: `success` |
| Reaparece código ee/ | Rama desechable con `backend/ee/x.py` confirmado: `scripts/check-libreseal-guard.sh` local → `GUARD FAILED: ee/ files are tracked: backend/ee/x.py` (exit 1). PR borrador #4 → check `guard`: `FAILURE`. PR cerrada y rama borrada |
| Sin publicación | El workflow solo declara `permissions: contents: read` y no contiene `docker login`, `docker push` ni pasos de release |

Nota: al ejecutar el guard antes de `git add`, pasa, porque comprueba ficheros versionados (`git ls-files`). Es el comportamiento correcto para CI.

## CI de los skills (`Dos2Locos/libreseal-skills`)

| Escenario | Resultado |
|---|---|
| Repositorio válido | `scripts/validate-skills.sh` en local: `all checks passed` (5 SKILL.md, shellcheck de 2 scripts, `nginx -t` del bloque completo; los 2 fragmentos marcados se omiten; sin `.env` ni tokens). En GitHub: check `validate` en `pass` en la PR #2 y en `main` (`32065a5`) |
| Skill con frontmatter incorrecto | `name: compose` en `docker-compose/SKILL.md` → `FAIL: front matter docker-compose/SKILL.md: name is 'compose', expected 'docker-compose'` |
| Plantilla de nginx inválida | `bogus_directive on;` en el bloque de `docker-compose-deployment.md` → `FAIL: nginx -t docker-compose/refs/docker-compose-deployment.md:111` con `nginx: [emerg] unknown directive "bogus_directive"` |
| Token versionado | Fichero con `pss_service:v2:abcSECRETVALUE123:def` → `FAIL: token-like value at leak.txt:1`; el valor aparece 0 veces en la salida |

Las pruebas negativas se hicieron en un worktree temporal. Un primer intento fallido, en el que no se creó el worktree, modificó temporalmente el repositorio real; se detectó y se restauró antes de confirmar nada.

## Protección de main

| Escenario | Resultado |
|---|---|
| Modo comprobación antes de aplicar | Los tres repositorios: `protection differs` (sin proteger). Sin cambios en GitHub |
| Nombres de checks | Coinciden con las ejecuciones reales (`gh pr checks` de libreseal #3 y skills #2; última ejecución de `main` de la CLI) |
| `--apply` | `protection applied` en los tres |
| Checks obligatorios configurados | `GET /branches/main/protection`:<br>• libreseal: `["guard","backend","frontend","compose-build"]`<br>• libreseal-cli: `["test / Go Test & Vet (ubuntu-latest)","test / Go Test & Vet (macos-latest)","test / Go Test & Vet (windows-latest)","install-from-source"]`<br>• libreseal-skills: `["validate"]`<br>En los tres: `strict=true`, `enforce_admins=true`, PR obligatoria con 0 aprobaciones, `allow_force_pushes=false`, `allow_deletions=false` |
| Reaplicar (idempotencia) | Segunda ejecución en modo comprobación: `protection: as documented` en los tres, exit 0 |
| Push directo rechazado | `git push origin HEAD:main` con token admin → `GH006: Protected branch update failed for refs/heads/main` / `protected branch hook declined` en libreseal, libreseal-cli y libreseal-skills |
| Merge con CI en rojo rechazado | PR #3 de skills con `SKILL.md` inválido: `validate` en `FAILURE`; ya fuera de borrador, `mergeStateStatus=BLOCKED` y `gh pr merge --merge` no fusiona; `main` sigue en `32065a53`. PR cerrada y rama borrada. No se probó `--admin` para no arriesgar `main`; la aplicación a admins queda demostrada por el push rechazado |

`openspec validate enable-fork-ci --strict`: válido.
