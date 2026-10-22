# HU-B-201 · Sanear el repositorio y configurar herramientas de calidad

| Campo | Valor |
|---|---|
| Fase | 2 · Reestructuración |
| Prioridad | Must |
| Estimación | 2 puntos |
| Depende de | — |
| Rama | `hu/HU-B-201-higiene-calidad` |

## Historia
**Como** equipo de desarrollo
**quiero** que el repositorio ignore secretos y entornos virtuales y tenga linter y SonarQube configurados
**para** que ningún secreto se suba por error y la calidad se mida desde el primer PR.

## Contexto
- El backend se separó del monorepo. Su `.gitignore` aún usa rutas `backend/.venv/`, `backend/.env`, que **ya no coinciden**: hoy `.env` y `venv/` aparecen como archivos sin seguimiento y podrían commitearse.
- `.env.example` usa `SUPABASE_KEY`; conviene nombrarla `SUPABASE_ANON_KEY` para alinearse con el frontend.
- No hay linter ni formateador ni `sonar-project.properties`.

## Alcance
**Incluye**
- `.gitignore` corregido para la raíz del repo.
- Ruff configurado en `pyproject.toml` como dependencia de desarrollo.
- `sonar-project.properties`.
- `.editorconfig`.
- `.env.example` con todas las variables actuales.

**No incluye**
- Mover archivos de código (HU-B-203).
- Corregir los errores que ruff reporte en código existente (se reportan en *Hallazgos*).

## Prompt de ejecución
```text
Ejecuta HU-B-201 en SIPE-SOUND-BACKEND. Objetivo: higiene del repo y tooling.
1) Reescribe .gitignore para rutas en la raíz: .env, .env.*, !.env.example,
   venv/, .venv/, __pycache__/, *.pyc, .ruff_cache/, .scannerwork/, .DS_Store,
   Thumbs.db, .vscode/ (excepto .vscode/extensions.json).
2) Verifica con `git status` que .env y venv/ ya NO aparecen. NO abras ni leas .env.
3) Agrega ruff como dependencia de desarrollo con `uv add --dev ruff` y la
   configuración [tool.ruff] de docs/fase-1-contrato/03-estandares-codigo.md.
4) Crea sonar-project.properties y .editorconfig según esta HU.
5) Actualiza .env.example (valores falsos). No cambies código de app/.
Entrega el PR con la plantilla del contrato de IA.
```

## Pasos
1. Reemplazar `.gitignore` (ver Prompt, punto 1).
2. `git rm --cached` de cualquier archivo que ya esté versionado y debería ignorarse (verificar con `git ls-files venv .env`). Si `.env` llegó a estar en el historial, **avisar** al equipo para rotar la `anon key` de Supabase.
3. `uv add --dev ruff` y pegar la configuración del contrato.
4. Crear `sonar-project.properties`:
   ```properties
   sonar.projectKey=sipe-sound-backend
   sonar.projectName=SIPE-SOUND Backend
   sonar.sources=app,migrations,scripts
   sonar.exclusions=**/__pycache__/**,venv/**,.venv/**
   sonar.python.version=3.11
   sonar.sourceEncoding=UTF-8
   ```
5. Crear `.editorconfig` (UTF-8, LF, 4 espacios en `*.py`, 2 en `*.{toml,yml,md}`, `insert_final_newline = true`).
6. `.env.example`:
   ```dotenv
   APP_ENV=local
   FLASK_DEBUG=1
   LOG_LEVEL=INFO
   CORS_ORIGINS=http://localhost:5173
   SUPABASE_URL=https://TU-PROYECTO.supabase.co
   SUPABASE_ANON_KEY=TU-ANON-KEY
   ```
   (Las variables de BD se agregan en HU-B-301.)
7. Ejecutar `uv run ruff check .` y copiar el **conteo** de errores por regla en *Hallazgos* (no corregirlos).

## Criterios de aceptación
```gherkin
Escenario: Los secretos no se pueden commitear
  Dado un archivo .env en la raíz del repositorio
  Cuando ejecuto git status
  Entonces .env no aparece como archivo sin seguimiento

Escenario: El linter está disponible
  Cuando ejecuto "uv run ruff check ."
  Entonces el comando se ejecuta con la configuración del contrato
```

## Verificación manual
```bash
git status --short          # no debe listar .env ni venv/
git check-ignore -v .env venv
uv run ruff --version
uv run ruff check . --statistics
```

## Definición de hecho específica
- [ ] `git check-ignore` confirma `.env` y `venv/` ignorados.
- [ ] `uv.lock` actualizado con ruff como dependencia de desarrollo.
- [ ] Ningún archivo de `app/` modificado.
