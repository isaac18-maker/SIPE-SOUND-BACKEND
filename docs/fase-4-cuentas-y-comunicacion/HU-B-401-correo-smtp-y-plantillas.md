# HU-B-401 · Enviar correos por Gmail SMTP con plantillas compatibles

| Campo | Valor |
|---|---|
| Fase | 4 · Cuentas y comunicación |
| Prioridad | Must |
| Estimación | 5 puntos |
| Depende de | HU-B-322 |
| Rama | `hu/HU-B-401-correo-smtp` |
| Referencia | [00-decisiones-fase-4.md](00-decisiones-fase-4.md) §2, §8 |

## Historia
**Como** equipo
**quiero** que el backend envíe sus propios correos por el SMTP de Gmail con plantillas versionadas
**para** controlar los códigos de registro y los enlaces de recuperación, y saber si cada correo salió.

## Contexto
- Hoy el único correo es la confirmación de Supabase Auth (su SMTP y sus plantillas, fuera del repo).
- No existe `app/infrastructure/correo*.py` ni `app/templates/`.
- `pyproject.toml` no tiene librerías de correo; Flask ya trae Jinja2.

## Alcance
**Incluye**
1. `app/infrastructure/correo_smtp.py`: `EnviadorSmtp.enviar(mensaje)` con `smtplib.SMTP`
   (`starttls()` con `ssl.create_default_context()`, `login`, `send_message`), tiempo de espera
   15 s, y `EnviadorArchivo` que escribe `.eml` en `tmp/correos/` (solo `APP_ENV=local`).
2. `app/services/correo_service.py`: `CorreoService.enviar(tipo, destinatario, contexto, usuario_id)`
   arma el `EmailMessage` (`multipart/alternative`: texto plano primero, HTML después),
   cabeceras `From: "SIPE-SOUND" <remitente>`, `Reply-To` opcional, `Message-ID`, `Date`,
   `Auto-Submitted: auto-generated`, y lo envía en segundo plano con un
   `ThreadPoolExecutor(max_workers=2)` del proceso. Al terminar registra el resultado en
   `envios_correo`. Interfaz `Enviador` (Protocol) para inyectarlo desde `app/container.py`.
3. Plantillas en `app/templates/correo/` (Jinja2, `autoescape=True`):
   - `_base.html` y `_base.txt` (marco común).
   - `verificar_correo`, `reautenticacion`, `restablecer_contrasena`, `contrasena_cambiada`,
     `cambiar_correo`, `correo_cambiado` — cada una `.html` + `.txt`, con su asunto en
     `app/services/correo_service.py` (`ASUNTOS`). Las que usan HU posteriores se crean aquí
     para revisar el diseño una sola vez.
4. Revisión `0018_envios_correo` (esquema): tabla `envios_correo` (00-decisiones §4), RLS sin
   políticas, `EXECUTE`/`SELECT` solo para el backend.
5. Configuración (`app/core/config.py`): `CORREO_MODO`, `SMTP_HOST`, `SMTP_PUERTO`, `SMTP_USUARIO`,
   `SMTP_CLAVE_APLICACION` (`SecretStr`), `CORREO_REMITENTE`, `CORREO_NOMBRE_REMITENTE`,
   `URL_FRONTEND`. Validaciones que impiden arrancar:
   - `CORREO_MODO=archivo` fuera de `local`.
   - `CORREO_MODO=smtp` sin host, usuario, clave o remitente.
   - `URL_FRONTEND` que no esté en `CORS_ORIGINS` o que termine en `/`.
6. `scripts/probar_correo.py --para <correo>`: envía la plantilla `verificar_correo` con el código
   `000000` marcado como prueba. Se niega a correr con `APP_ENV=production` sin `--confirmar`.
7. `.env.example`, `docs/configuracion-entornos.md` (cómo crear la contraseña de aplicación) y
   contrato 02 (nueva pieza de infraestructura).

**No incluye**
- Ningún flujo que use los correos (B-402 en adelante).
- Colas externas (Redis, Celery) ni reintentos automáticos: un envío fallido queda `fallido` y
  se reenvía desde el flujo que lo pidió (B-402, B-405).
- Correos de la mensajería interna (00-decisiones §6).

## Diseño de las plantillas (compatibilidad)

Clientes de referencia: Gmail (web, Android, iOS), Outlook (Microsoft 365 escritorio en Windows,
Outlook.com), Apple Mail (macOS, iOS) y Yahoo.

| Regla | Por qué |
|---|---|
| Maquetación con `<table role="presentation">`, ancho máximo 600 px, fluida en móvil | Outlook en Windows usa el motor de Word: no entiende flex, grid ni `max-width` en `div`. |
| **Todo** el CSS en línea (`style=""`); un `<style>` solo para `@media` y modo oscuro | Gmail elimina partes de `<style>` en algunos clientes. |
| Botón "a prueba de balas": `<a>` con relleno en una celda + bloque `<!--[if mso]>` con VML | El botón se ve igual en Outlook. |
| Fuente `Arial, Helvetica, sans-serif`; el código en `'Courier New', monospace`, 28 px, `letter-spacing: 6px` | Las fuentes web (Baloo 2, Inter) no cargan en la mayoría de clientes. |
| Sin imágenes obligatorias, sin SVG, sin JavaScript, sin formularios, sin fondos con imagen | Gmail quita SVG; muchos clientes bloquean imágenes. La marca es texto ("SIPE-SOUND"). |
| `<html lang="es">`, `<meta name="color-scheme" content="light dark">`, `<meta name="supported-color-schemes">` | Lectores de pantalla y modo oscuro sin colores invertidos ilegibles. |
| Paleta clara con contraste ≥ 4.5:1 (texto `#1B2140` sobre `#FFFFFF`; botón `#4B42D6` con texto blanco, 6.9:1) | En correo no existen los tokens CSS del frontend: el hex en plantillas de correo está permitido (la regla R7 es del frontend). |
| Texto de vista previa (*preheader*) oculto al inicio | Lo que se lee en la bandeja antes de abrir. |
| Versión `.txt` con el mismo contenido y el enlace completo | Clientes solo texto y filtros de spam. |
| El enlace también aparece como texto debajo del botón | Si el botón no funciona. |
| Pie: por qué llega el correo, que el equipo nunca pide la contraseña y qué hacer si no fue la persona | Seguridad y confianza. |

Voz (contrato 05 §7 del frontend): tuteo, frases cortas, sin exclamaciones dobles ni emojis.
Ejemplo de asunto: "Tu código de SIPE-SOUND: 482913" (el código en el asunto se ve en la
notificación del celular; el cuerpo repite que vence en 15 minutos).

## Prompt de ejecución
```text
Ejecuta HU-B-401 en SIPE-SOUND-BACKEND. Implementa el envío de correos con smtplib (biblioteca
estándar) por smtp.gmail.com:587 con STARTTLS y contraseña de aplicación; sin dependencias
nuevas. Plantillas Jinja2 en app/templates/correo/ (HTML + texto) siguiendo la tabla de
compatibilidad de la HU: tablas, CSS en línea, botón con VML para Outlook, sin SVG ni imágenes
obligatorias. El envío corre en un ThreadPoolExecutor y registra el resultado en envios_correo
(revisión 0018). Nunca registres en logs ni en la base el código, el enlace, la clave SMTP ni
el cuerpo del correo; en envios_correo.error solo un código corto (p. ej. "smtp_auth",
"smtp_timeout"). Capas: api → services → repositories; la infraestructura se inyecta desde
app/container.py. Documenta cada variable en .env.example y docs/configuracion-entornos.md.
```

## Pasos
1. Configuración y validaciones (§5 del alcance) + `.env.example`.
2. `Enviador` (Protocol), `EnviadorSmtp`, `EnviadorArchivo`; `tmp/correos/` en `.gitignore`.
3. Plantillas base y las seis plantillas con su `.txt`.
4. Revisión 0018, modelo `EnvioCorreo` y `SqlEnvioCorreoRepository`.
5. `CorreoService` con el ejecutor en segundo plano y el registro del resultado.
6. `scripts/probar_correo.py`.
7. Documentación (configuración, contrato 02).

## Criterios de aceptación
```gherkin
Escenario: Envío por Gmail
  Dado CORREO_MODO=smtp con una cuenta de Gmail y su contraseña de aplicación
  Cuando ejecuto scripts/probar_correo.py --para mi@correo.co
  Entonces el correo llega con remitente "SIPE-SOUND"
  Y envios_correo tiene una fila con estado "enviado"

Escenario: Credenciales inválidas
  Dado una contraseña de aplicación equivocada
  Cuando se envía un correo
  Entonces envios_correo registra estado "fallido" con error "smtp_auth"
  Y el log no contiene la clave ni el contenido del correo

Escenario: Modo archivo
  Dado APP_ENV=local y CORREO_MODO=archivo
  Cuando se envía un correo
  Entonces aparece un .eml en tmp/correos/ que se abre en un cliente de correo

Escenario: Configuración incoherente
  Dado APP_ENV=production y CORREO_MODO=archivo
  Entonces la app no arranca y el error nombra CORREO_MODO

Escenario: Plantillas en distintos clientes
  Cuando abro el correo de prueba en Gmail web, Gmail Android, Outlook escritorio y Apple Mail iOS
  Entonces el código y el botón se leen completos, sin desbordes, en claro y en oscuro
```

## Verificación manual
```bash
uv run ruff check . && uv run ruff format --check .
uv run python scripts/check_migrations.py
uv run alembic upgrade head && uv run alembic downgrade -1 && uv run alembic upgrade head
uv run python -m scripts.probar_correo --para tu@correo.co
# Capturas del correo en los cuatro clientes de referencia (claro y oscuro) en el PR.
```

## Definición de hecho específica
- [ ] `grep -rn "SMTP_CLAVE\|password" app/infrastructure/correo_smtp.py` no muestra la clave en ningún `logger.`.
- [ ] Capturas en Gmail web, Gmail Android, Outlook escritorio y Apple Mail (claro y oscuro).
- [ ] `.env.example` y `docs/configuracion-entornos.md` actualizados.
