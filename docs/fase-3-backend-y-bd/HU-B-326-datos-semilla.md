# HU-B-326 · Sembrar la ruta real, los cursos y las cuentas de prueba

| Campo | Valor |
|---|---|
| Fase | 3 · Backend y BD |
| Prioridad | Must |
| Estimación | 5 puntos |
| Depende de | HU-B-325 (base en la revisión 0017), HU-B-324 |
| Rama | `hu/HU-B-326-datos-semilla` |
| Relacionada | HU-F-315 (inicio del estudiante), HU-F-307 a F-310 (atril) |

## Historia
**Como** equipo
**quiero** una base con contenido real de guitarra, cursos y cuentas de prueba por rol
**para** probar y mostrar la plataforma completa sin depender de datos sueltos o de prueba.

## Contexto
Tras aplicar las migraciones 0012–0017 (HU-B-325), la base tenía el contenido inicial migrado
desde los quizzes: 6 bloques, 8 lecciones y 3 ejercicios incompletos. Ningún curso, ningún docente y
todos los perfiles con rol `estudiante`. No se podía probar el atril ni el inicio del estudiante.

## Alcance
**Incluye**
- `scripts/sembrar_datos.py` y `scripts/semilla/` (`contenido.py`, `cursos.py`, `sql.py`):
  - **Borra** en una sola transacción el contenido y su actividad: `bloques`, `lecciones`,
    `ejercicios`, `evaluaciones`, `preguntas_evaluacion`, `intentos_evaluacion`, `cursos`,
    `curso_bloques`, `inscripciones`, `retroalimentaciones`, `progreso_lecciones`,
    `progreso_ejercicios`. `TRUNCATE` sin `CASCADE`: si otra tabla dependiera de ellas, falla y
    revierte.
  - **Conserva** las cuentas (`auth.users`), los perfiles y el catálogo de `acordes`.
  - **Ruta real** para principiantes: 6 bloques (Fundamentos, Primeros acordes menores, Acordes
    mayores abiertos, Ritmo y rasgueo, Progresiones y cambios fluidos, La cejilla), 22 lecciones con
    contenido didáctico, 13 ejercicios con BPM, compás y pasos, y una evaluación global publicada por
    bloque (5 preguntas, aprueba con 80 %). Los acordes usan solo nombres del catálogo y el texto
    coincide con sus diagramas (dedos y trastes).
  - **Cursos** del docente de prueba: "Guitarra 7°A" (código `K7M2Q9XA`, bloques 1–4) con el
    estudiante de prueba inscrito y una retroalimentación, y "Guitarra 9°B · Intermedio" (código
    `R4TB8HWE`, bloques 3–6).
  - **Cuentas de prueba** en el dominio reservado `example.com` (RFC 2606, nunca reciben correo):
    `docente.prueba@example.com` (rol docente, por preautorización) y
    `estudiante.prueba@example.com`. Se crean ya confirmadas en `auth.users` + `auth.identities`,
    sin enviar correos; el trigger `handle_new_user` crea su perfil. Si ya existen, se restablece
    su contraseña.
  - **Contraseñas** generadas al ejecutar (16 caracteres, letras y números) y mostradas una sola vez:
    no se guardan en el repositorio.
  - **Administrador**: la cuenta indicada con `--admin` pasa a rol `admin` (debe existir).
  - **Avance de demostración** solo para la cuenta de prueba (6 lecciones, 2 ejercicios y 2 intentos
    de la evaluación del bloque 1, con fechas de los últimos 9 días), para verificar el inicio.
- Protección: exige `--confirmar borrar-contenido`; sin ella no hace nada.

**No incluye**: tocar cuentas reales distintas del administrador indicado, cambiar el catálogo de
acordes, datos de estudiantes reales.

## Uso
```bash
uv run python -m scripts.respaldar_datos              # siempre antes
uv run python -m scripts.sembrar_datos --admin correo@dominio.co --confirmar borrar-contenido
```

## Criterios de aceptación
```gherkin
Escenario: Transacción única
  Dado un error en cualquier paso de la semilla
  Entonces la base queda exactamente como estaba

Escenario: Ruta completa para el estudiante de prueba
  Cuando inicia sesión y consulta GET /ruta
  Entonces ve 6 bloques: el 1 aprobado, el 2 disponible con 2 de 4 lecciones y el resto bloqueados

Escenario: Atril con datos
  Cuando el docente de prueba inicia sesión
  Entonces ve sus 2 cursos, el estudiante inscrito en 7°A y su retroalimentación

Escenario: Administrador
  Entonces la cuenta indicada con --admin tiene rol admin y su contraseña no cambia
```

## Ejecución en la base (2026-10-23)
- Respaldos previos: `respaldos/20261023_224231` (revisión 0011) y `respaldos/20261023_225147`
  (revisión 0017, justo antes de la semilla).
- Resultado: 6 bloques, 22 lecciones, 13 ejercicios, 6 evaluaciones con 30 preguntas, 2 cursos,
  8 bloques en rutas de curso, 1 inscripción, 1 retroalimentación; 5 perfiles (1 admin, 1 docente,
  3 estudiantes).
- Verificado: inicio de sesión de ambas cuentas por `POST /auth/sesion` (200) y `GET /me`, `/ruta`,
  `/progreso/resumen` y `/progreso/actividad` del estudiante con su token.
