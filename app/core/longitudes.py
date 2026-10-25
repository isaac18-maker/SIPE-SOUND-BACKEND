# =========================================================
# Limites de los campos que escriben las personas (HU-B-320).
# Fuente unica para los esquemas de entrada; la base aplica los mismos
# limites con CHECK (revision 0013) y el frontend los replica en sus
# formularios (contrato de API, seccion 7). Cambiar uno exige cambiar los tres.
# =========================================================

# Personas y cuentas
NOMBRE_PERSONA_MIN, NOMBRE_PERSONA_MAX = 2, 80
# El apellido tiene los mismos limites que el nombre (HU-B-407).
APELLIDO_PERSONA_MIN, APELLIDO_PERSONA_MAX = NOMBRE_PERSONA_MIN, NOMBRE_PERSONA_MAX
EMAIL_MAX = 254  # RFC 5321
PASSWORD_MIN, PASSWORD_MAX = 8, 72  # 72: limite de bcrypt en Supabase Auth

# Contenido y cursos
TITULO_MIN, TITULO_MAX = 3, 120  # bloques, lecciones, ejercicios y cursos
DESCRIPCION_MAX = 2000
CONTENIDO_LECCION_MAX = 20000
NOMBRE_ACORDE_MIN, NOMBRE_ACORDE_MAX = 1, 20
DESCRIPCION_ACORDE_MAX = 500
MENSAJE_RETROALIMENTACION_MIN, MENSAJE_RETROALIMENTACION_MAX = 1, 1000

# Mensajeria interna (HU-B-409)
ASUNTO_MIN, ASUNTO_MAX = 3, 120
CUERPO_MENSAJE_MIN, CUERPO_MENSAJE_MAX = 1, 4000

# Numeros
BPM_MINIMO, BPM_MAXIMO = 20, 300
DURACION_MIN_MINIMO, DURACION_MIN_MAXIMO = 1, 600

# Compas del ejercicio: "4/4", "3/4", "6/8", "12/8"...
PATRON_COMPAS = "^(2|3|4|5|6|7|9|12)/(2|4|8)$"

# Listas
MAXIMO_ACORDES = 24
MAXIMO_TEMAS = 20
MAXIMO_PASOS = 30
# Largo de cada elemento de las listas
TEMA_MAX = 60
PASO_MAX = 300

# Evaluaciones, segun HU-B-308
ENUNCIADO_MIN, ENUNCIADO_MAX = 3, 300
OPCION_MIN, OPCION_MAX = 1, 120
OPCIONES_MIN, OPCIONES_MAX = 2, 6
PREGUNTAS_MIN, PREGUNTAS_MAX = 1, 50
APROBACION_MIN, APROBACION_MAX = 50, 100
INTENTOS_MAX_MIN, INTENTOS_MAX_MAX = 1, 10

# Busqueda y paginacion
BUSQUEDA_MAX = 80
POR_PAGINA_MAX = 100
