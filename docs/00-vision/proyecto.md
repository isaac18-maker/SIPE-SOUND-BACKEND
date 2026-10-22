# SIPE-SOUND · Visión del producto

> Documento de contexto. Todo agente de IA o desarrollador debe leerlo **una vez**
> antes de ejecutar cualquier HU. Explica *para qué* existe el código.

## Planteamiento

Desarrollar una plataforma web que permita a personas principiantes aprender
guitarra de manera autoguiada, con contenido organizado por niveles de
dificultad y un sistema que registre el avance de cada estudiante.

### Objetivos del proyecto

1. Facilitar el uso de una aplicación enfocada en el aprendizaje básico de
   instrumentos de cuerda, empezando por la guitarra.
2. Analizar otras ayudas que se le pueden aportar a la comunidad musical.
3. Lanzar una aplicación atractiva, útil y sencilla con esas funciones musicales.

## Misión

En SIPE-SOUND facilitamos el aprendizaje de la guitarra a estudiantes mediante
una plataforma web interactiva, progresiva y accesible. A través de lecciones
guiadas, ejercicios prácticos y seguimiento del progreso, cada estudiante puede
aprender a su propio ritmo, medir su avance y desarrollar su talento musical.
Trabajamos de la mano con docentes e instituciones educativas, ofreciendo
herramientas seguras y fáciles de usar que fortalecen la formación artística en
el aula y acercan la música a más jóvenes de Colombia, sin importar su contexto
o recursos.

## Visión 2031

Ser la plataforma de referencia en Colombia para aprender guitarra en el aula,
usada por colegios de todo el país y con presencia en Latinoamérica. Contará con:

- Panel para docentes.
- Rutas de aprendizaje progresivas.
- Logros que motiven la práctica.
- Reconocimiento de audio que evalúe lo que toca el estudiante.
- Otros instrumentos, versión móvil y uso con poca conectividad (zonas rurales).
- Modelo sostenible de licencias institucionales con acceso de bajo costo.

## Cómo se traduce la visión en decisiones técnicas

| Elemento de la visión | Decisión técnica que lo habilita hoy |
|---|---|
| Panel docente | Rol `docente` en `profiles`, entidades `cursos`, `inscripciones`, `evaluaciones` (Fase 3). |
| Rutas progresivas | `bloques` ordenados por `orden_index`; desbloqueo por aprobación de evaluación. |
| Logros | El progreso se guarda con FK reales y fechas → los logros serán consultas, no datos duplicados. |
| Otros instrumentos | El catálogo (`bloques`, `lecciones`, `ejercicios`) no asume "guitarra" en nombres de columnas. Futuro: columna `instrumento`. |
| Poca conectividad | API con respuestas pequeñas, paginadas y cacheables; frontend con code-splitting por ruta. |
| Licencias institucionales | Arquitectura en capas que permite añadir `instituciones` sin reescribir servicios. |
| Audio | Fuera de alcance. No se agregan dependencias de audio hasta que exista una HU. |

## Roles del sistema

| Rol | Qué puede hacer |
|---|---|
| **Visitante** | Ver catálogo público (bloques, lecciones, acordes, ejercicios). |
| **Estudiante** | Todo lo del visitante + presentar evaluaciones, registrar progreso, unirse a cursos con código. |
| **Docente** | Gestionar sus cursos, lecciones, ejercicios y evaluaciones; ver estudiantes inscritos y su progreso; dar retroalimentación. |
| **Administrador** | Gestionar el catálogo global y asignar el rol docente. |

## Glosario de dominio

| Término | Significado |
|---|---|
| **Bloque** | Unidad de la ruta de aprendizaje. Agrupa lecciones y cierra con una evaluación. |
| **Lección** | Contenido guiado (teoría + acordes + temas). Pertenece a un bloque. |
| **Ejercicio** | Práctica concreta con BPM, compás y pasos. Puede asociarse a una lección. |
| **Acorde** | Elemento del catálogo con diagrama (trastes, dedos, cejilla). |
| **Evaluación** | Conjunto de preguntas que el estudiante presenta. Puede ser de bloque (global) o de curso (creada por un docente). |
| **Intento** | Cada vez que un estudiante presenta una evaluación. Se guarda el historial. |
| **Curso** | Grupo de estudiantes a cargo de un docente. Se ingresa con un código de invitación. |
| **Progreso** | Registro por estudiante y por contenido (porcentaje y completado). |
