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
| `SUPABASE_ANON_KEY` | *anon* / *publishable key* del proyecto | La del proyecto de producción | No (pública), pero solo en el backend |
| `AUTH_COOKIE_SECURE` | vacío (automático = `0`) | `1` (o vacío: automático = `1`) | No |
| `AUTH_COOKIE_SAMESITE` | `Lax` | `Lax` (mismo sitio) o `None` (dominios distintos) | No |
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
SUPABASE_ANON_KEY=<anon-o-publishable-key>
AUTH_COOKIE_SECURE=
AUTH_COOKIE_SAMESITE=Lax
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
SUPABASE_ANON_KEY=<anon-o-publishable-key>
AUTH_COOKIE_SECURE=1
AUTH_COOKIE_SAMESITE=Lax
DATABASE_URL=postgresql://postgres.<proyecto>:<password>@aws-0-<region>.pooler.supabase.com:5432/postgres
SQLALCHEMY_ECHO=0
```

## Detalle por variable

### `APP_ENV`
Indica en qué entorno corre el backend.

| Valor | Efecto |
|---|---|
| `production` | Activa las protecciones: Alembic exige `-x confirmar=production` y `scripts.promover_admin` exige `--confirmar`. Además, `FLASK_DEBUG=1` o `SQLALCHEMY_ECHO=1` impiden arrancar. |
| `staging` | Base de pruebas remota: sin confirmaciones. |
| `local` | Base en tu computador. Si `DATABASE_URL` apunta a una base **remota**, Alembic y los scripts **se bloquean** hasta que corrijas `APP_ENV`. |

Solo se aceptan esos tres valores (sin importar mayúsculas). Cualquier otro, como
`produccion` o `prod`, impide arrancar y el error lista los valores válidos.

> ⚠️ **Regla de oro:** si `DATABASE_URL` apunta a la base de producción, `APP_ENV`
> debe ser `production` **aunque estés en tu computador**. La protección depende de
> esta variable, no de dónde corre el código. Hoy el proyecto tiene **una sola base**
> (la de producción), así que en la práctica tu `.env` local también lleva
> `APP_ENV=production`.
>
> Si lo olvidas, Alembic te avisa: `APP_ENV=local pero DATABASE_URL apunta a una base remota`.

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
Nivel mínimo de los mensajes del log: `DEBUG` < `INFO` < `WARNING` < `ERROR` (solo esos valores).

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
- **Producción:** solo el dominio público del frontend. **Nunca `*`**: la app no arranca con `*` ni con orígenes sin `http://`/`https://`. La `/` final se elimina sola.

### `SUPABASE_URL`
Dirección del proyecto de Supabase. El backend la usa para validar los tokens de
inicio de sesión: comprueba el emisor y descarga las claves públicas de
`<SUPABASE_URL>/auth/v1/.well-known/jwks.json`.

- **Dónde está:** Supabase → Project Settings → Data API → *Project URL*.
- **No es secreta.** Desde HU-B-322 el frontend ya no la necesita.

### `SUPABASE_ANON_KEY` (HU-B-322)
Clave **pública** del proyecto. El backend la usa para hablar con Supabase Auth en nombre del
frontend: `POST /auth/registro`, `POST /auth/sesion`, `POST /auth/sesion/renovar` y
`DELETE /auth/sesion`.

- **Dónde está:** Supabase → Project Settings → **API Keys** → *anon public* (claves legadas)
  o la *publishable key* (`sb_publishable_…`). Cualquiera de las dos sirve.
- **Nunca** la *service_role* ni la *secret key* (`sb_secret_…`): ignoran RLS y se retiraron en HU-B-321.
- No es secreta (no da más permisos que un visitante), pero desde HU-B-322 solo vive en el
  backend: el navegador ya no la recibe.
- Si falta, la app arranca igual (Alembic y los scripts no la usan) y las rutas `/auth/*`
  responden `503` con el mensaje "falta configurar SUPABASE_ANON_KEY".

### `AUTH_COOKIE_SECURE` y `AUTH_COOKIE_SAMESITE` (HU-B-322)
El *refresh token* nunca llega a JavaScript: viaja en la cookie `sipe_refresh` (`HttpOnly`,
`Path=/api/v1/auth`, 30 días). El *access token* va en el cuerpo de la respuesta y el
frontend lo guarda **solo en memoria**.

| Variable | Valores | Efecto |
|---|---|---|
| `AUTH_COOKIE_SECURE` | vacío · `1` · `0` | Vacío = automático: `0` con `APP_ENV=local`, `1` en `staging`/`production`. Fuera de `local`, `0` impide arrancar. |
| `AUTH_COOKIE_SAMESITE` | `Lax` · `Strict` · `None` | `Lax` si frontend y API son el **mismo sitio** (`localhost:5173`/`localhost:5000`, o `app.sipesound.co`/`api.sipesound.co`). `None` solo si están en **dominios distintos** (p. ej. `*.vercel.app` y `*.onrender.com`); exige `AUTH_COOKIE_SECURE=1`. |

> Abre el frontend y la API con el **mismo nombre de host** en local (`localhost` en ambos).
> `localhost` y `127.0.0.1` son sitios distintos para el navegador y la cookie no viajaría.

### `DATABASE_URL` 🔒
**Única** conexión a PostgreSQL. La usan la app y Alembic (migraciones).

- **Dónde está:** Supabase → **Connect** → Connection string → Method: **Session pooler** → copiar y reemplazar `[YOUR-PASSWORD]`.
- **Forma:** `postgresql://postgres.<proyecto>:<password>@aws-0-<region>.pooler.supabase.com:5432/postgres`
- **Puerto 5432** (Session pooler). **Nunca el 6543** (Transaction pooler): rompe las migraciones y Alembic lo rechaza.
- Si la contraseña tiene `@ # / : %`, genera una nueva solo con letras y números (Project Settings → Database → Reset database password).
- **Es secreta:** da control total de la base. Solo en el `.env` o en los secretos del servidor; nunca en el frontend, en git ni en el chat. Si se filtra, cambia la contraseña de la base.

### Variables que ya NO existen
`SUPABASE_SERVICE_ROLE_KEY` y `FRONTEND_URL` (HU-B-318) se retiraron en HU-B-321;
`DATABASE_URL_MIGRATIONS`, `DATA_BACKEND` y `SUPABASE_JWKS_URL`, en HU-B-315.
Si siguen en tu `.env`, bórralas: la app las ignora. `SUPABASE_ANON_KEY` **volvió** en
HU-B-322, ahora para Supabase Auth (no para la API REST). El único secreto sigue siendo `DATABASE_URL`.

### Configuración de cuentas en Supabase (no son variables del backend)
Desde HU-B-322 el registro y el inicio de sesión pasan por el backend (`/auth/*`), que llama a
Supabase Auth. En el panel de Supabase:
- Authentication → Providers → Email: **Confirm email activado** (obligatorio: el rol docente
  se asigna al confirmar el correo) y contraseña mínima 8 con letras y dígitos.
- Authentication → URL Configuration → **Site URL**: `<url-del-frontend>/login` (a donde vuelve
  la persona desde el correo de confirmación; el backend no envía `redirect_to`).
- Authentication → URL Configuration → *Redirect URLs*: `<url-del-frontend>/login`.
- Project Settings → Data API: con el frontend fuera de Supabase, nadie necesita la API REST
  pública. Mantén **RLS activado** en todas las tablas de `public` (o quita `public` de
  *Exposed schemas*): la clave pública sigue existiendo y RLS es lo que impide leer tablas con ella.
- ⚠️ El correo incluido en Supabase envía **muy pocos correos por hora**. Para un salón
  completo, configura un SMTP propio en Authentication → Emails → SMTP Settings.

### `SQLALCHEMY_ECHO`
Si es `1`, escribe en el log **cada sentencia SQL con sus valores**.

- **Local:** `0`; `1` solo mientras depuras una consulta.
- **Producción:** siempre `0` (con `APP_ENV=production` la app no arranca si vale `1`). Los valores pueden incluir datos de estudiantes y el volumen de log crece mucho.

## Despliegue en producción

- Arrancar con **waitress** (incluido en las dependencias; funciona en Windows y Linux), **no** con `run.py`:
  ```bash
  uv run waitress-serve --listen=0.0.0.0:8000 --threads=8 wsgi:app
  ```
- Las variables se configuran en el panel del proveedor de hosting (sección *Environment variables* o *Secrets*), no con un archivo `.env` subido al servidor.
- Antes de migrar: respaldar los datos y revisar el SQL (`migrations/README.md`, P10):
  ```bash
  uv run python -m scripts.respaldar_datos     # crea respaldos/<fecha>/ (ignorado por git)
  ```

## Verificar la configuración

```bash
uv run python -c "from app import create_app; create_app(); print('configuracion OK')"
uv run alembic current        # en producción: uv run alembic -x confirmar=production current
```

Si falta una variable, el error dice cuál (sin mostrar valores):
`ConfiguracionInvalida: Configuracion invalida. Revisa estas variables de entorno: DATABASE_URL`
