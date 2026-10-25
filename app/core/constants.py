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
PROPOSITO_VERIFICAR_CORREO = "verificar_correo"
PROPOSITO_RESTABLECER = "restablecer_contrasena"
PROPOSITO_REAUTENTICAR = "reautenticar"
PROPOSITO_REAUTENTICADO = "reautenticado"
PROPOSITO_CAMBIAR_CORREO = "cambiar_correo"
VIGENCIA_CODIGO_MIN = {
    PROPOSITO_VERIFICAR_CORREO: 15,
    PROPOSITO_RESTABLECER: 15,
    PROPOSITO_REAUTENTICAR: 10,
    PROPOSITO_REAUTENTICADO: 5,
    PROPOSITO_CAMBIAR_CORREO: 15,
}
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

ENVIO_ENVIADO = "enviado"
ENVIO_FALLIDO = "fallido"
ESTADOS_ENVIO = (ENVIO_ENVIADO, ENVIO_FALLIDO)
