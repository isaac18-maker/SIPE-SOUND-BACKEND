# HU-B-312 · Exponer la retroalimentación al estudiante y retirar lo legado

| Campo | Valor |
|---|---|
| Fase | 3 · Backend y BD |
| Prioridad | Should |
| Estimación | 5 puntos |
| Depende de | HU-B-308, HU-B-310, **HU-F-304, HU-F-306 desplegadas** |
| Rama | `hu/HU-B-312-ruta-y-limpieza` |

## Historia
**Como** estudiante
**quiero** leer los comentarios que mi docente me deja
**para** saber qué debo reforzar en mi práctica.

**Como** equipo
**quiero** eliminar las tablas y rutas de compatibilidad
**para** no mantener dos modelos de datos.

## Alcance
**Incluye**
1. `GET /api/v1/cursos/{id}/retroalimentaciones` (marca `leida_en`).
2. Retiro del prefijo `/api/*` sin versión.
3. Revisión `0010` **destructiva aprobada**:
   - `drop table quiz_preguntas` y `drop table progreso` (previo respaldo).
   - `drop column duracion` en `lecciones` y `ejercicios`.
   - Cabecera `Destructiva: si` y `# destructivo-aprobado: HU-B-312` en cada operación.
   - `downgrade()` recrea las estructuras (vacías) y documenta que los datos se restauran desde el respaldo.
4. Eliminar `app/infrastructure/supabase_rest.py`, repositorios `supabase/` y `DATA_BACKEND`.

## Prompt de ejecución
```text
Ejecuta HU-B-312 en SIPE-SOUND-BACKEND SOLO si el usuario confirma que
HU-F-304 y HU-F-306 están desplegadas (el frontend ya no usa /api/* ni /quiz/*).
- Antes de 0010, pide al usuario el pg_dump de respaldo y anota la fecha en el PR.
- Genera 0010 con -x allow_destructive=true y marca cada operación.
- Verifica en local que check_migrations.py pasa y que downgrade recrea las tablas.
- Elimina el código legado y DATA_BACKEND. Actualiza el contrato de API (§6 Compatibilidad).
```

## Criterios de aceptación
```gherkin
Escenario: Retroalimentación leída
  Dado un comentario del docente sin leer
  Cuando el estudiante consulta GET /api/v1/cursos/{id}/retroalimentaciones
  Entonces recibe el comentario y leida_en queda registrado

Escenario: Legado retirado
  Cuando consulto GET /api/lecciones
  Entonces recibo 404
```

## Verificación manual
```bash
uv run python scripts/check_migrations.py   # debe pasar gracias a las marcas
uv run alembic upgrade head && uv run alembic downgrade -1 && uv run alembic upgrade head
grep -rn "supabase_rest\|DATA_BACKEND" app/ || echo "legado eliminado"
```

## Definición de hecho específica
- [ ] Respaldo de producción tomado y verificado (`pg_restore --list` lee el archivo).
- [ ] `04-contrato-api.md` sin la sección de compatibilidad.
