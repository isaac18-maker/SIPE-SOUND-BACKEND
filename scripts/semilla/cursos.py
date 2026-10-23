"""Cursos y cuentas de prueba de la semilla (HU-B-326).

Las cuentas de prueba usan el dominio reservado example.com (RFC 2606): nunca reciben correo.
Las contrasenas no viven aqui: el script las genera al ejecutarse y las muestra una sola vez.
"""

from typing import Any

DOCENTE_PRUEBA = {"email": "docente.prueba@example.com", "nombre": "Docente de Prueba"}
ESTUDIANTE_PRUEBA = {"email": "estudiante.prueba@example.com", "nombre": "Estudiante de Prueba"}

# Codigos de invitacion validos: 8 caracteres de A-Z y 2-9 sin 0, O, 1, I ni L.
CURSOS: list[dict[str, Any]] = [
    {
        "nombre": "Guitarra 7°A",
        "descripcion": "Grupo de la mañana. Empezamos por los fundamentos y los primeros acordes.",
        "nivel": "principiante",
        "codigo": "K7M2Q9XA",
        # Posiciones (1..6) de los bloques de contenido.BLOQUES en la ruta del curso.
        "ruta": [1, 2, 3, 4],
        "inscribir_estudiante": True,
        "retroalimentacion": (
            "Buen trabajo con la afinación. Esta semana practica el cambio de Em a Am a "
            "60 BPM, diez minutos al día."
        ),
    },
    {
        "nombre": "Guitarra 9°B · Intermedio",
        "descripcion": (
            "Progresiones, ritmo y cejilla para quienes ya dominan los acordes abiertos."
        ),
        "nivel": "intermedio",
        "codigo": "R4TB8HWE",
        "ruta": [3, 4, 5, 6],
        "inscribir_estudiante": False,
        "retroalimentacion": None,
    },
]

# Avance de demostracion SOLO para la cuenta de prueba, para verificar el inicio (HU-F-315).
# lecciones / ejercicios: numero global de leccion o posicion del ejercicio -> (dias atras, datos).
PROGRESO_DEMO: dict[str, Any] = {
    "lecciones": {1: 9, 2: 9, 3: 8, 4: 7, 5: 4, 6: 2},
    "ejercicios": {
        1: {"dias": 8, "porcentaje": 100, "completado": True, "mejor_bpm": 70},
        2: {"dias": 1, "porcentaje": 50, "completado": False, "mejor_bpm": 55},
    },
    # Intentos de evaluacion: posicion del bloque -> [(dias atras, correctas de 5)].
    "intentos": {1: [(7, 3), (6, 5)]},
}
