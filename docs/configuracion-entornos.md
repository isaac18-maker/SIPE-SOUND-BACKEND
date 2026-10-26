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
| `CORS_ORIGINS` | `http://localhost:5173` | URL pública del frontend, p. ej. `https://app.sipesound.co` | **Sí** (obligatoria, sin valor por defecto) |
| `SUPABASE_URL` | URL del proyecto de Supabase | La misma (o la del proyecto de producción si tienen dos) | No |
| `SUPABASE_ANON_KEY` | *anon* / *publishable key* del proyecto | La del proyecto de producción | No (pública), pero solo en el backend |
| `AUTH_COOKIE_SECURE` | vacío (automático = `0`) | `1` (o vacío: automático = `1`) | No |
| `AUTH_COOKIE_SAMESITE` | `Lax` | `Lax` (mismo sitio) o `None` (dominios distintos) | No |
| `CORREO_MODO` | vacío (automático = `archivo`) | vacío (automático = `smtp`) | No |
| `SMTP_USUARIO` | opcional con `archivo`; la cuenta de Gmail con `smtp` | cuenta de Gmail que envía | No |
| `SMTP_CLAVE_APLICACION` | opcional con `archivo` | contraseña de aplicación de Gmail | **Sí** |
| `URL_FRONTEND` | `http://localhost:5173` | URL pública del frontend (igual a `CORS_ORIGINS`) | No |
| `CODIGOS_SECRETO` | cadena aleatoria de 32+ caracteres | otra distinta, 32+ caracteres | **Sí** |
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
CODIGOS_SECRETO=<cadena-aleatoria-de-32-o-más-caracteres>
CORREO_MODO=archivo
URL_FRONTEND=http://localhost:5173
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
CODIGOS_SECRETO=<otra-cadena-aleatoria-de-32-o-más-caracteres>
CORREO_MODO=smtp
SMTP_USUARIO=<cuenta-de-gmail>
SMTP_CLAVE_APLICACION=<contraseña-de-aplicación>
URL_FRONTEND=https://<dominio-del-frontend>
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

### `CODIGOS_SECRETO` 🔒 (HU-B-402)
Clave del HMAC-SHA256 con que se guardan los códigos de verificación (registro, restablecer
contraseña, cambio de correo). En la base solo queda el hash: quien robe la tabla no puede usar
ningún código sin esta clave.

- **Cómo crearla:** `python -c "import secrets; print(secrets.token_urlsafe(48))"`.
- **Obligatoria** (mínimo 32 caracteres): sin ella la app, Alembic y los scripts no arrancan y el
  error nombra `CODIGOS_SECRETO`. Usa una distinta en cada entorno.
- Cambiarla invalida los códigos pendientes: quienes los pidieron tendrán que pedir uno nuevo.
- Solo en el `.env` o en los secretos del servidor; nunca en git, el frontend ni el chat.

### Correo saliente: `CORREO_MODO`, `SMTP_*`, `CORREO_*` y `URL_FRONTEND` (HU-B-401)
El backend envía sus propios correos (código de verificación, enlace para restablecer la
contraseña y avisos de seguridad) por el SMTP de Gmail, con `smtplib` y STARTTLS.

| Variable | Valores | Efecto |
|---|---|---|
| `CORREO_MODO` | vacío · `smtp` · `archivo` | `smtp` envía de verdad. `archivo` deja cada correo como `.eml` en `tmp/correos/` (se abre con cualquier cliente de correo); solo con `APP_ENV=local`. Vacío = `archivo` en local y `smtp` en `staging`/`production`. |
| `SMTP_HOST`, `SMTP_PUERTO` | `smtp.gmail.com`, `587` | No se cambian con Gmail. |
| `SMTP_USUARIO` | correo de Gmail | Cuenta que envía. |
| `SMTP_CLAVE_APLICACION` 🔒 | 16 caracteres | **No** es la contraseña de la cuenta. Se escribe con o sin los espacios que muestra Google. |
| `CORREO_REMITENTE` | correo | Vacío = `SMTP_USUARIO`. Otro valor debe ser un alias verificado en Gmail (*Enviar como*), o Gmail lo reemplaza. |
| `CORREO_NOMBRE_REMITENTE` | texto | Nombre visible; por defecto `SIPE-SOUND`. |
| `URL_FRONTEND` | origen | Base de los enlaces de los correos. Sin `/` final y presente en `CORS_ORIGINS`. |

**Crear la contraseña de aplicación**
1. En la cuenta de Gmail que enviará: Seguridad → activar la **Verificación en dos pasos**.
2. Seguridad → *Contraseñas de aplicaciones* → nombre "SIPE-SOUND" → copiar los 16 caracteres.
3. Pegarlos en `SMTP_CLAVE_APLICACION` (solo en el `.env` o en los secretos del servidor).
4. Probar: `uv run python -m scripts.probar_correo --para tu@correo.co`.

> ⚠️ Gmail personal permite unos 500 destinatarios por día (Workspace, unos 2000). Los correos
> son solo transaccionales; la mensajería interna no envía correos. Si la clave se filtra,
> revócala en la misma pantalla de Google.

Si falta algo con `smtp`, la app no arranca y el error nombra la variable
(`CORREO_MODO=smtp exige SMTP_USUARIO, SMTP_CLAVE_APLICACION`).

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
- Authentication → Providers → Email: **Confirm email DESACTIVADO** (HU-B-402): el correo con el
  código lo envía el backend. ⚠️ Desactívalo **después** de aplicar las migraciones 0019 y 0020 y
  desplegar la API, nunca antes: la 0019 mueve la asignación del rol docente a la verificación del
  código; sin ella, quien se registre con un correo preautorizado ajeno sería docente.
  Contraseña mínima 8 con letras y dígitos.
- Authentication → URL Configuration → **Site URL**: `<url-del-frontend>/login` (ya no se usa
  para confirmar cuentas; déjala por si Supabase envía otros correos).
- Authentication → URL Configuration → *Redirect URLs*: `<url-del-frontend>/login`.
- Project Settings → Data API: con el frontend fuera de Supabase, nadie necesita la API REST
  pública. Mantén **RLS activado** en todas las tablas de `public` (o quita `public` de
  *Exposed schemas*): la clave pública sigue existiendo y RLS es lo que impide leer tablas con ella.
- Los correos ya no salen de Supabase sino del SMTP de Gmail del backend (ver `CORREO_MODO`).

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
