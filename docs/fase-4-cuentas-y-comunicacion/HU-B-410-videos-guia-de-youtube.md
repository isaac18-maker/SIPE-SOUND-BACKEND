# HU-B-410 · Video guía de YouTube en bloques, lecciones, ejercicios y acordes

| Campo | Valor |
|---|---|
| Fase | 4 · Cuentas y comunicación |
| Prioridad | Should |
| Estimación | 3 puntos |
| Depende de | HU-B-306, HU-B-309 |
| Rama | `hu/HU-B-410-videos-guia` |
| Relacionada | HU-F-408 |
| Referencia | [00-decisiones-fase-4.md](00-decisiones-fase-4.md) §7 |

## Historia
**Como** docente o administrador
**quiero** agregar a un bloque, una lección, un ejercicio o un acorde el enlace de un video que ya subí a YouTube
**para** que el estudiante vea cómo se toca mientras practica.

## Contexto
- `bloques`, `lecciones`, `ejercicios` y `acordes` no tienen campos de video.
- Las lecciones y ejercicios se editan con `registrar_crud` (`app/api/v1/_crud_contenido.py`) en
  `/docente/*`; los bloques en `/admin/bloques`; los acordes **no** tienen endpoints de edición.

## Alcance
**Incluye**
1. Revisión `0026_videos_guia` (esquema), en las cuatro tablas:
   - `video_youtube_id text null`, CHECK `video_youtube_id ~ '^[A-Za-z0-9_-]{11}$'`.
   - `video_inicio_seg integer null`, CHECK 0–43200, y CHECK `video_inicio_seg is null or video_youtube_id is not null`.
2. `app/core/youtube.py` (función pura): `extraer_video(url) -> (id, inicio_seg | None)`.
   Acepta `https://www.youtube.com/watch?v=ID`, `https://youtu.be/ID`, `/embed/ID`, `/shorts/ID`,
   `/live/ID`, `m.youtube.com`, `music.youtube.com` y `youtube-nocookie.com`, con `t=90`,
   `t=1m30s` o `start=90` (en la consulta o en el fragmento `#t=`). Un tiempo ilegible o fuera
   de rango se ignora (no invalida el enlace). Rechaza cualquier otro
   dominio, listas sin `v=` y URLs de más de 300 caracteres → 400 "Pega el enlace de un video de YouTube
   (por ejemplo, https://youtu.be/…)."
3. Entrada y salida:
   - Esquemas de crear/editar de lección, ejercicio y bloque aceptan `video_url: str | null`
     (`null` quita el video) y `video_inicio_seg` opcional (si viene, gana sobre el `t=` de la URL).
   - Acordes (catálogo global): `PUT /admin/acordes/{id}/video` `{video_url, video_inicio_seg?}` y
     `DELETE /admin/acordes/{id}/video`.
   - Todas las lecturas (públicas y del panel) agregan `video: {youtube_id, inicio_seg} | null`.
4. Permisos (00-decisiones §7): docente en sus lecciones y ejercicios; admin en todo. Sin cambios
   en las reglas de `registrar_crud`.
5. Contrato 04 (§4.1, §4.3, §4.4, §5 `LeccionOut` y §7: `video_url` máx. 300, solo YouTube).

**No incluye**
- Subir videos al servidor ni a YouTube.
- Validar que el video exista o sea público (se haría con la API de YouTube y una clave; el
  frontend muestra un aviso si el reproductor no puede cargarlo).
- Varios videos por contenido.

## Prompt de ejecución
```text
Ejecuta HU-B-410 en SIPE-SOUND-BACKEND. Agrega video_youtube_id (11 caracteres) y
video_inicio_seg a bloques, lecciones, ejercicios y acordes (revisión 0026 con CHECK). La API
recibe video_url y guarda solo el id con app/core/youtube.py (función pura que acepta solo
dominios de YouTube). Las lecturas devuelven video: {youtube_id, inicio_seg} o null. El docente
edita el video de sus lecciones y ejercicios; el admin, todo (bloques y acordes con
PUT/DELETE /admin/acordes/{id}/video). Sin dependencias nuevas ni llamadas a YouTube.
```

## Pasos
1. Revisión 0026 con `downgrade()`.
2. `app/core/youtube.py` y su validador Pydantic reutilizable.
3. Esquemas de entrada/salida y endpoints de acordes.
4. Contrato 04.

## Criterios de aceptación
```gherkin
Escenario: Formatos aceptados
  Cuando guardo una lección con video_url "https://youtu.be/dQw4w9WgXcQ?t=42"
  Entonces GET /lecciones/{id} devuelve video {"youtube_id":"dQw4w9WgXcQ","inicio_seg":42}

Escenario: Otro dominio
  Cuando envío video_url "https://vimeo.com/123"
  Entonces recibo 400 "Pega el enlace de un video de YouTube…"

Escenario: Quitar el video
  Cuando edito la lección con video_url null
  Entonces su video queda en null

Escenario: Acorde solo admin
  Cuando un docente envía PUT /admin/acordes/3/video
  Entonces recibe 403

Escenario: Lección ajena
  Cuando un docente pone video en la lección de otro docente
  Entonces recibe 404 (igual que al editarla hoy)
```

## Verificación manual
```bash
uv run ruff check . && uv run ruff format --check .
uv run python scripts/check_migrations.py
uv run alembic upgrade head && uv run alembic downgrade -1 && uv run alembic upgrade head
uv run python -c "from app.core.youtube import extraer_video as e; print(e('https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=1m30s'))"
# ('dQw4w9WgXcQ', 90)
```

## Definición de hecho específica
- [ ] `extraer_video` probada a mano con los seis formatos de la HU y tres URLs inválidas (salida en el PR).
- [ ] Ninguna lectura devuelve la URL original, solo el id.
