PORCENTAJE_APROBACION = 80
PORCENTAJE_MINIMO = 0
PORCENTAJE_MAXIMO = 100

TIPO_LECCION = "leccion"
TIPO_EJERCICIO = "ejercicio"

ROL_ESTUDIANTE = "estudiante"
ROL_DOCENTE = "docente"
ROL_ADMIN = "admin"
ROLES = (ROL_ESTUDIANTE, ROL_DOCENTE, ROL_ADMIN)

ESTADO_BORRADOR = "borrador"
ESTADO_PUBLICADO = "publicado"
ESTADO_ARCHIVADO = "archivado"
ESTADOS_CONTENIDO = (ESTADO_BORRADOR, ESTADO_PUBLICADO, ESTADO_ARCHIVADO)

# Codigo de invitacion a un curso: 8 caracteres sin ambiguedades (sin 0/O/1/I/L).
ALFABETO_CODIGO = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
LARGO_CODIGO = 8

# Evaluaciones (HU-B-308). El umbral por defecto solo se usa al crear.
EVALUACION_BORRADOR = "borrador"
EVALUACION_PUBLICADA = "publicada"
EVALUACION_CERRADA = "cerrada"
ESTADOS_EVALUACION = (EVALUACION_BORRADOR, EVALUACION_PUBLICADA, EVALUACION_CERRADA)
TIPO_PREGUNTA_OPCION_UNICA = "opcion_unica"

# Estado de un bloque en la ruta del estudiante (lo calcula RutaService).
BLOQUE_BLOQUEADO = "bloqueado"
BLOQUE_DISPONIBLE = "disponible"
BLOQUE_APROBADO = "aprobado"

# Inicio del estudiante (HU-B-324): actividad reciente y avance por dia.
ZONA_HORARIA = "America/Bogota"
ACTIVIDAD_DIAS_MIN = 7
ACTIVIDAD_DIAS_MAX = 90
ACTIVIDAD_DIAS_DEFECTO = 28
ACTIVIDAD_RECIENTES = 10
ACORDES_POR_BLOQUE = 6

# Correos transaccionales (HU-B-401): un tipo por plantilla en app/templates/correo/.
CORREO_VERIFICAR = "verificar_correo"
CORREO_REAUTENTICACION = "reautenticacion"
CORREO_RESTABLECER = "restablecer_contrasena"
CORREO_CONTRASENA_CAMBIADA = "contrasena_cambiada"
CORREO_CAMBIAR_CORREO = "cambiar_correo"
CORREO_CORREO_CAMBIADO = "correo_cambiado"
TIPOS_CORREO = (
    CORREO_VERIFICAR,
    CORREO_REAUTENTICACION,
    CORREO_RESTABLECER,
    CORREO_CONTRASENA_CAMBIADA,
    CORREO_CAMBIAR_CORREO,
    CORREO_CORREO_CAMBIADO,
)
# Codigos de verificacion (HU-B-402): proposito -> minutos de vigencia. Nunca mas de 15.
# El del registro dura 1 minuto (HU-B-416): la persona ve la cuenta regresiva y pide otro al vencer.
PROPOSITO_VERIFICAR_CORREO = "verificar_correo"
PROPOSITO_RESTABLECER = "restablecer_contrasena"
PROPOSITO_REAUTENTICAR = "reautenticar"
PROPOSITO_REAUTENTICADO = "reautenticado"
PROPOSITO_CAMBIAR_CORREO = "cambiar_correo"
VIGENCIA_CODIGO_MIN = {
    PROPOSITO_VERIFICAR_CORREO: 1,
    PROPOSITO_RESTABLECER: 15,
    PROPOSITO_REAUTENTICAR: 10,
    PROPOSITO_REAUTENTICADO: 5,
    PROPOSITO_CAMBIAR_CORREO: 15,
}
VIGENCIA_VERIFICACION_SEGUNDOS = VIGENCIA_CODIGO_MIN[PROPOSITO_VERIFICAR_CORREO] * 60
PROPOSITOS_CODIGO = tuple(VIGENCIA_CODIGO_MIN)
CODIGO_DIGITOS = 6
CODIGO_INTENTOS_MAX = 5
# Entre un codigo y el siguiente para la misma cuenta (evita llenar la bandeja de alguien).
CODIGO_ESPERA_SEGUNDOS = 60
# Entre un enlace de restablecimiento y el siguiente para la misma cuenta (HU-B-403).
RECUPERACION_ESPERA_SEGUNDOS = 120

MENSAJE_SIN_CONFIRMAR = (
    "Aún no confirmas tu correo. Escribe el código de 6 dígitos que te enviamos o pide uno nuevo."
)

# Estado de una cuenta (se calcula, no se guarda).
CUENTA_PENDIENTE = "pendiente_verificacion"
CUENTA_ACTIVA = "activa"
CUENTA_SUSPENDIDA = "suspendida"
MENSAJE_SUSPENDIDA = "Tu cuenta está suspendida. Habla con el administrador."

# Terminos y condiciones editables (HU-B-411): un solo documento vigente con numero de version.
TIPO_TERMINOS = "terminos"
TERMINOS_MAX = 60000
MENSAJE_TERMINOS_PENDIENTES = "Lee y acepta los términos y condiciones actualizados para continuar."
CODIGO_TERMINOS_PENDIENTES = "TERMINOS_PENDIENTES"

# Auditoria del administrador (HU-B-405). Las que usan HU posteriores ya estan permitidas.
ACCIONES_ADMIN = (
    "reenviar_verificacion",
    "verificar_manual",
    "suspender",
    "reactivar",
    "eliminar",
    "cambiar_rol",
    "revocar_curso",
    "reasignar_curso",
    "permiso_nombre",
)

ENVIO_ENVIADO = "enviado"
ENVIO_FALLIDO = "fallido"
ESTADOS_ENVIO = (ENVIO_ENVIADO, ENVIO_FALLIDO)

# Mensajeria interna (HU-B-409). Los limites por hora los mide la base (cuenta mensajes
# reales), no un contador en memoria: valen aunque haya varios procesos.
ALCANCE_USUARIO = "usuario"
ALCANCE_CURSO = "curso"
ALCANCE_ESTUDIANTES_DOCENTE = "estudiantes_docente"
ALCANCE_ROL_ESTUDIANTE = "rol_estudiante"
ALCANCE_ROL_DOCENTE = "rol_docente"
ALCANCE_ROL_ADMIN = "rol_admin"
ALCANCE_TODOS = "todos"
ALCANCES_MENSAJE = (
    ALCANCE_USUARIO,
    ALCANCE_CURSO,
    ALCANCE_ESTUDIANTES_DOCENTE,
    ALCANCE_ROL_ESTUDIANTE,
    ALCANCE_ROL_DOCENTE,
    ALCANCE_ROL_ADMIN,
    ALCANCE_TODOS,
)
# A que puede escribir cada rol (00-decisiones-fase-4, seccion 6).
ALCANCES_POR_ROL = {
    ROL_ADMIN: frozenset(
        {
            ALCANCE_USUARIO,
            ALCANCE_ROL_ESTUDIANTE,
            ALCANCE_ROL_DOCENTE,
            ALCANCE_ROL_ADMIN,
            ALCANCE_TODOS,
        }
    ),
    ROL_DOCENTE: frozenset(
        {
            ALCANCE_USUARIO,
            ALCANCE_CURSO,
            ALCANCE_ESTUDIANTES_DOCENTE,
            ALCANCE_ROL_DOCENTE,
            ALCANCE_ROL_ADMIN,
        }
    ),
    ROL_ESTUDIANTE: frozenset({ALCANCE_USUARIO}),
}
MENSAJES_POR_HORA = {ROL_ESTUDIANTE: 20, ROL_DOCENTE: 60, ROL_ADMIN: 120}
AVISOS_DE_GRUPO_POR_HORA = 10
EXTRACTO_MENSAJE_MAX = 140
DESTINATARIOS_SUGERIDOS_MAX = 20
FILTROS_BANDEJA = ("recibidos", "enviados", "no_leidos", "archivados")
