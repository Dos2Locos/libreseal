# Spec Delta

## Purpose

Define cómo se identifica LibreSeal como fork independiente de Phase Console y cómo cumple las licencias y atribuciones heredadas en servidor, CLI y skills.

## ADDED Requirements

### Requirement: Marca LibreSeal propia
La interfaz web, el título de las páginas, el favicon, el logotipo y los mensajes visibles SHALL usar el nombre LibreSeal y recursos visuales propios de LibreSeal, no el logotipo ni el nombre comercial de Phase como marca del producto.

#### Scenario: Página de inicio de sesión
- **WHEN** un usuario abre `https://<host>/login`
- **THEN** el título del documento contiene "LibreSeal", el logotipo mostrado es el de LibreSeal y no aparece el logotipo de Phase

#### Scenario: Recursos estáticos
- **WHEN** se solicita `https://<host>/favicon.ico` o el logotipo de la barra de navegación
- **THEN** el recurso servido procede de `frontend/public` de LibreSeal y su origen está documentado como recurso propio

### Requirement: Aviso de no afiliación
LibreSeal SHALL declarar en el README y en la interfaz (pantalla de inicio de sesión o "Acerca de") que es un fork independiente de Phase Console, sin afiliación ni respaldo de Phi Security Inc. / Phase.

#### Scenario: Aviso en la UI
- **WHEN** un usuario abre `https://<host>/login`
- **THEN** la página muestra un texto que identifica LibreSeal como fork independiente de Phase sin afiliación

#### Scenario: Aviso en README
- **WHEN** se lee `README.md` del repositorio `libreseal`
- **THEN** contiene una sección de relación con Phase con enlace a `phasehq/console` y la declaración de no afiliación

### Requirement: Conservación de licencias y atribuciones
Los repositorios LibreSeal SHALL conservar los avisos de copyright de Phi Security Inc., el fichero `LICENSE` MIT original, la licencia GPL-3.0 del CLI, la licencia MIT de los skills y el historial git heredado.

#### Scenario: Licencias presentes
- **WHEN** se inspecciona la raíz de `libreseal`, `libreseal-cli` y `libreseal-skills`
- **THEN** cada repositorio contiene su `LICENSE` original sin eliminar el copyright de Phi Security Inc. y `git log` incluye los commits de upstream

### Requirement: Ausencia de código bajo licencia Enterprise
El árbol de LibreSeal y las imágenes construidas desde él SHALL NOT contener ficheros de los directorios `ee/` de Phase Console ni código derivado de ellos.

#### Scenario: Árbol sin ee
- **WHEN** se ejecuta `git ls-files | grep -E '(^|/)ee/'` en la rama de LibreSeal
- **THEN** la salida está vacía

#### Scenario: Imágenes sin ee
- **WHEN** se ejecuta `docker compose run --rm backend sh -c 'test ! -e /app/ee'` y se inspecciona el build del frontend
- **THEN** el comando termina con código 0 y ningún módulo del bundle procede de `frontend/ee`
