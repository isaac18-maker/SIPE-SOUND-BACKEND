# Configuración por entorno (`.env`)

Qué valor poner en cada variable del backend, en **local** (tu computador) y en
**producción** (el servidor que usan los estudiantes). La plantilla es
[`.env.example`](../.env.example); el `.env` real **nunca** se sube a git.

## Resumen rápido

| Variable | Local | Producción | ¿Secreta? |
|---|---|---|---|
| `APP_ENV` | `local` | `production` | No |
| `FLASK_DEBUG` | `1` | `0` | No |
| `LOG_LEVEL` | `DEBUG` o `INFO` | `INFO` | No |
| `CORS_ORIGINS` | `http://localhost:5173` | URL pública del frontend, p. ej. `https://app.sipesound.co` | No |
| `SUPABASE_URL` | URL del proyecto de Supabase | La misma (o la del proyecto de producción si tienen dos) | No |
| `DATABASE_URL` | Session pooler del proyecto que uses | Session pooler del proyecto de producción | **Sí** |
| `SQLALCHEMY_ECHO` | `0` (o `1` solo para depurar) | `0` | No |

Plantillas listas para copiar:

```dotenv
# ---------- .env LOCAL ----------
APP_ENV=local
FLASK_DEBUG=1
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:5173
SUPABASE_URL=https://<proyecto>.supabase.co
DATABASE_URL=postgresql://postgres.<proyecto>:<password>@aws-0-<region>.pooler.supabase.com:5432/postgres
SQLALCHEMY_ECHO=0
```

```dotenv
# ---------- .env PRODUCCION ----------
APP_ENV=production
FLASK_DEBUG=0
LOG_LEVEL=INFO
CORS_ORIGINS=https://<dominio-del-frontend>
SUPABASE_URL=https://<proyecto>.supabase.co
DATABASE_URL=postgresql://postgres.<proyecto>:<password>@aws-0-<region>.pooler.supabase.com:5432/postgres
SQLALCHEMY_ECHO=0
```

## Detalle por variable

### `APP_ENV`
Indica en qué entorno corre el backend.

| Valor | Efecto |
|---|---|
| `production` | Activa las protecciones: `alembic upgrade/downgrade/stamp/current/check` exigen `-x confirmar=production` y `scripts/promover_admin` exige `--confirmar`. |
| `local`, `staging` u otro | Sin esas confirmaciones. |

> ⚠️ **Regla de oro:** si `DATABASE_URL` apunta a la base de producción, `APP_ENV`
> debe ser `production` **aunque estés en tu computador**. La protección depende de
> esta variable, no de dónde corre el código. Hoy el proyecto tiene **una sola base**
> (la de producción), así que en la práctica tu `.env` local también lleva
> `APP_ENV=production`.
>
> Se compara el texto exacto: `Production`, `produccion` o `prod` **no** activan la
> protección.

### `FLASK_DEBUG`
Solo lo usa el servidor de desarrollo (`uv run python run.py`).

| Valor | Efecto |
|---|---|
| `1` | Recarga automática al guardar archivos y página de error interactiva. |
| `0` | Sin depurador. |

> ⚠️ **Nunca `1` en producción.** El depurador de Flask permite ejecutar código
> Python en el servidor desde el navegador. En producción, además, no se usa `run.py`
> sino `wsgi.py` con un servidor WSGI (ver "Despliegue" abajo), que ignora esta variable.

### `LOG_LEVEL`
Nivel mínimo de los mensajes del log: `DEBUG` < `INFO` < `WARNING` < `ERROR`.

| Entorno | Recomendado | Por qué |
|---|---|---|
| Local | `INFO` (o `DEBUG` al investigar un problema) | Ver qué pasa en cada petición. |
| Producción | `INFO` | Registra errores y tokens rechazados (solo el motivo, nunca el token). Usa `WARNING` si el volumen de logs es un problema. |

El backend nunca registra contraseñas, tokens ni cadenas de conexión, en ningún nivel.

### `CORS_ORIGINS`
Qué páginas web pueden llamar a la API desde el navegador. Si el origen del
frontend no está en la lista, el navegador bloquea las peticiones con un error de CORS.

- **Formato:** orígenes exactos separados por comas, con esquema y puerto y **sin `/` final**:
  `https://app.sipesound.co,https://www.sipesound.co`
- **Local:** `http://localhost:5173` (puerto de Vite). Si abres el frontend como
  `http://127.0.0.1:5173`, agrégalo también: es otro origen para el navegador.
- **Producción:** solo el dominio público del frontend. **Nunca `*`.**

### `SUPABASE_URL`
Dirección del proyecto de Supabase. El backend la usa para validar los tokens de
inicio de sesión: comprueba el emisor y descarga las claves públicas de
`<SUPABASE_URL>/auth/v1/.well-known/jwks.json`.

- **Dónde está:** Supabase → Project Settings → Data API → *Project URL*.
- **No es secreta**: el frontend tiene la misma.

### `DATABASE_URL` 🔒
**Única** conexión a PostgreSQL. La usan la app y Alembic (migraciones).

- **Dónde está:** Supabase → **Connect** → Connection string → Method: **Session pooler** → copiar y reemplazar `[YOUR-PASSWORD]`.
- **Forma:** `postgresql://postgres.<proyecto>:<password>@aws-0-<region>.pooler.supabase.com:5432/postgres`
- **Puerto 5432** (Session pooler). **Nunca el 6543** (Transaction pooler): rompe las migraciones y Alembic lo rechaza.
- Si la contraseña tiene `@ # / : %`, genera una nueva solo con letras y números (Project Settings → Database → Reset database password).
- **Es secreta:** da control total de la base. Solo en el `.env` o en los secretos del servidor; nunca en el frontend, en git ni en el chat. Si se filtra, cambia la contraseña de la base.

### `SQLALCHEMY_ECHO`
Si es `1`, escribe en el log **cada sentencia SQL con sus valores**.

- **Local:** `0`; `1` solo mientras depuras una consulta.
- **Producción:** siempre `0`. Los valores pueden incluir datos de estudiantes y el volumen de log crece mucho.

## Despliegue en producción

- Arrancar con `wsgi.py` y un servidor WSGI (gunicorn en Linux, waitress en Windows), **no** con `run.py`.
- Las variables se configuran en el panel del proveedor de hosting (sección *Environment variables* o *Secrets*), no con un archivo `.env` subido al servidor.
- Antes de migrar: revisar `migrations/README.md` (P10, respaldo y revisión del SQL).

## Verificar la configuración

```bash
uv run python -c "from app import create_app; create_app(); print('configuracion OK')"
uv run alembic current        # en producción: uv run alembic -x confirmar=production current
```

Si falta una variable, el error dice cuál (sin mostrar valores):
`ConfiguracionInvalida: Configuracion invalida. Revisa estas variables de entorno: DATABASE_URL`
