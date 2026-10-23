"""Ruta de aprendizaje semilla (HU-B-326): bloques, lecciones, ejercicios y evaluaciones.

Contenido real para principiantes. Los acordes usan solo nombres del catalogo (`acordes`) y las
preguntas se verificaron contra sus diagramas (p. ej. Em = 022000, Am = x02210, D = xx0232).
Las lecciones se numeran en orden global (1, 2, 3...), como las muestra la ruta.
Respetan los limites de app/core/longitudes.py.
"""

from typing import Any

Contenido = dict[str, Any]


def _p(*parrafos: str) -> str:
    """Parrafos separados por una linea en blanco (asi los muestra la leccion)."""
    return "\n\n".join(parrafos)


def _pregunta(enunciado: str, opciones: list[str], correcta: int) -> Contenido:
    return {"enunciado": enunciado, "opciones": opciones, "correcta": correcta}


BLOQUE_FUNDAMENTOS: Contenido = {
    "titulo": "Fundamentos de la guitarra",
    "descripcion": "Conoce tu instrumento, siéntate bien con él y afínalo antes del primer acorde.",
    "nivel": "principiante",
    "lecciones": [
        {
            "titulo": "Partes de la guitarra",
            "descripcion": "Clavijero, mástil, trastes, boca y puente: para qué sirve cada uno.",
            "duracion_min": 10,
            "acordes": [],
            "temas": ["clavijero", "mástil", "trastes", "boca", "puente"],
            "contenido": _p(
                "La guitarra acústica tiene tres zonas: la cabeza o clavijero, el mástil y el "
                "cuerpo. En el clavijero están las clavijas, que tensan cada cuerda y sirven "
                "para afinar.",
                "El mástil está dividido por trastes, unas barras metálicas delgadas. Cuando "
                "pisas una cuerda justo detrás de un traste acortas la parte que vibra y la nota "
                "sube. Los puntos del diapasón (trastes 3, 5, 7, 9 y 12) te ayudan a ubicarte.",
                "En el cuerpo está la boca, el agujero por donde sale el sonido, y el puente, "
                "donde se sujetan las cuerdas. La cejuela, al final del mástil, es la pieza "
                "blanca que separa las cuerdas antes del clavijero.",
                "Las cuerdas se numeran de la más delgada (1.ª, Mi agudo) a la más gruesa "
                "(6.ª, Mi grave). Esa numeración la usarás en todas las lecciones.",
            ),
        },
        {
            "titulo": "Postura y cómo sostener la guitarra",
            "descripcion": "Una buena postura evita dolores y hace que los acordes suenen limpios.",
            "duracion_min": 10,
            "acordes": [],
            "temas": ["postura", "mano izquierda", "mano derecha", "púa"],
            "contenido": _p(
                "Siéntate en una silla sin brazos, con la espalda recta y los pies apoyados. "
                "Apoya la curva del cuerpo de la guitarra sobre la pierna derecha (si eres "
                "diestro) y deja el mástil levemente inclinado hacia arriba.",
                "El pulgar de la mano izquierda va detrás del mástil, más o menos a la altura "
                "del dedo medio. Los dedos pisan con la punta, arqueados, para no tocar las "
                "cuerdas vecinas.",
                "La mano derecha rasguea sobre la boca. Si usas púa, sostenla entre el pulgar y "
                "el costado del índice, dejando asomar solo la punta.",
                "Relaja los hombros. Si sientes tensión en la muñeca, para, sacude las manos y "
                "vuelve a empezar: tocar no debe doler.",
            ),
        },
        {
            "titulo": "Afinación estándar",
            "descripcion": "Afina las seis cuerdas en Mi, La, Re, Sol, Si, Mi con un afinador.",
            "duracion_min": 15,
            "acordes": [],
            "temas": ["afinación estándar", "afinador", "E A D G B E"],
            "contenido": _p(
                "La afinación estándar, de la 6.ª a la 1.ª cuerda, es Mi, La, Re, Sol, Si, Mi. "
                "En cifrado americano: E, A, D, G, B, E. Una frase para recordarla: «Mi Amigo "
                "Dice Gracias Bien Educado».",
                "Usa un afinador de pinza o una aplicación. Pulsa una cuerda al aire y gira su "
                "clavija despacio: si la nota está baja, tensa; si está alta, afloja un poco y "
                "vuelve a subir hasta el centro. Afinar subiendo hace que la cuerda se mantenga.",
                "Afina siempre antes de practicar. Las cuerdas nuevas se desafinan rápido los "
                "primeros días; es normal.",
            ),
        },
        {
            "titulo": "Leer diagramas de acordes y tablatura",
            "descripcion": "Entiende cómo se dibujan los acordes y las tablaturas de la ruta.",
            "duracion_min": 12,
            "acordes": ["Em"],
            "temas": ["diagrama de acorde", "tablatura", "× y ○"],
            "contenido": _p(
                "Un diagrama de acorde muestra el mástil de frente: las líneas verticales son "
                "las cuerdas (la 6.ª a la izquierda) y las horizontales, los trastes. La línea "
                "gruesa de arriba es la cejuela.",
                "Los puntos indican dónde pisar y el número es el dedo: 1 índice, 2 medio, "
                "3 anular, 4 meñique. Una × sobre la cuerda significa que no se toca y un ○ "
                "que se toca al aire, sin pisar.",
                "La tablatura usa seis líneas horizontales, una por cuerda, con la 1.ª arriba. "
                "Cada número es el traste que se pisa; un 0 es la cuerda al aire.",
                "Prueba con Em: pisa la 5.ª y la 4.ª cuerda en el traste 2 con los dedos 2 y 3, "
                "y rasguea las seis cuerdas.",
            ),
        },
    ],
    "ejercicios": [
        {
            "leccion": 2,
            "nombre": "Cuerdas al aire con metrónomo",
            "descripcion": "Pulsa cada cuerda al aire al ritmo del metrónomo, sin perder el pulso.",
            "bpm": 60,
            "compas": "4/4",
            "duracion_min": 5,
            "acordes": [],
            "pasos": [
                "Coloca el metrónomo a 60 BPM.",
                "Pulsa la 6.ª cuerda al aire en cada tiempo durante un compás.",
                "Pasa a la 5.ª cuerda y repite, hasta llegar a la 1.ª.",
                "Vuelve de la 1.ª a la 6.ª sin detenerte.",
                "Cuando no pierdas ningún tiempo, sube a 70 BPM.",
            ],
        },
    ],
    "evaluacion": [
        _pregunta(
            "¿Cuál es la afinación estándar de la 6.ª a la 1.ª cuerda?",
            ["E A D G B E", "E B G D A E", "A D G B E A", "D G B E A D"],
            0,
        ),
        _pregunta(
            "¿Qué parte de la guitarra sostiene las clavijas?",
            ["El puente", "El clavijero", "La boca", "La cejuela"],
            1,
        ),
        _pregunta(
            "En un diagrama de acorde, ¿qué significa una × sobre una cuerda?",
            ["Se toca al aire", "No se toca", "Se pisa con el dedo 1", "Se toca dos veces"],
            1,
        ),
        _pregunta(
            "En un diagrama de acorde, ¿qué significa un ○ sobre una cuerda?",
            [
                "Se toca al aire, sin pisar",
                "No se toca",
                "Se pisa en el traste 1",
                "Es la nota más aguda",
            ],
            0,
        ),
        _pregunta(
            "¿Qué número tiene la cuerda más delgada (Mi agudo)?",
            ["6.ª", "1.ª", "3.ª", "5.ª"],
            1,
        ),
    ],
}

BLOQUE_MENORES: Contenido = {
    "titulo": "Primeros acordes menores",
    "descripcion": "Em, Am y Dm: tres acordes cómodos para empezar a tocar canciones.",
    "nivel": "principiante",
    "lecciones": [
        {
            "titulo": "El acorde Em",
            "descripcion": "Mi menor: dos dedos y las seis cuerdas sonando.",
            "duracion_min": 12,
            "acordes": ["Em"],
            "temas": ["Mi menor", "dedos 2 y 3"],
            "contenido": _p(
                "Em (Mi menor) es el acorde más sencillo de la guitarra. Pisa la 5.ª cuerda en "
                "el traste 2 con el dedo 2 y la 4.ª cuerda en el traste 2 con el dedo 3.",
                "Rasguea las seis cuerdas. Luego tócalas una por una: todas deben sonar claras. "
                "Si alguna se apaga, arquea más los dedos para no rozarla.",
                "Los acordes menores tienen un carácter más serio o melancólico que los "
                "mayores. Escucha la diferencia cuando aprendas E en el bloque 3.",
            ),
        },
        {
            "titulo": "El acorde Am",
            "descripcion": "La menor: tres dedos y la 6.ª cuerda sin tocar.",
            "duracion_min": 12,
            "acordes": ["Am"],
            "temas": ["La menor", "cuerda que no se toca"],
            "contenido": _p(
                "Am (La menor) usa tres dedos: el 1 en la 2.ª cuerda, traste 1; el 2 en la 4.ª "
                "cuerda, traste 2; y el 3 en la 3.ª cuerda, traste 2.",
                "Rasguea desde la 5.ª cuerda: la 6.ª no se toca (tiene una × en el diagrama).",
                "Comprueba cada cuerda por separado. La 1.ª suele apagarse con la yema del dedo "
                "1: inclínalo un poco hacia el traste.",
            ),
        },
        {
            "titulo": "El acorde Dm",
            "descripcion": "Re menor: cuatro cuerdas y un sonido más agudo.",
            "duracion_min": 12,
            "acordes": ["Dm"],
            "temas": ["Re menor", "cuatro cuerdas"],
            "contenido": _p(
                "Dm (Re menor) se toca solo en las cuatro cuerdas agudas: la 6.ª y la 5.ª no "
                "suenan. La 4.ª cuerda va al aire.",
                "Pisa la 3.ª cuerda en el traste 2 con el dedo 2, la 2.ª en el traste 3 con el "
                "dedo 3 y la 1.ª en el traste 1 con el dedo 1.",
                "Apunta el rasgueo a las cuerdas agudas. Al principio ayuda empezar el golpe "
                "desde la 4.ª cuerda y no desde arriba.",
            ),
        },
        {
            "titulo": "Cambio entre Em y Am",
            "descripcion": "Tu primer cambio de acorde, lento y sin pausas.",
            "duracion_min": 15,
            "acordes": ["Em", "Am"],
            "temas": ["cambio de acorde", "dedos que se mueven juntos"],
            "contenido": _p(
                "Em y Am comparten la 4.ª cuerda en el traste 2. Al cambiar, mueve los dedos "
                "como una forma: primero piensa dónde van, luego bájalos al mismo tiempo.",
                "Practica sin rasguear: forma Em, levanta la mano 1 cm, forma Am y vuelve. "
                "Haz diez repeticiones lentas antes de usar el metrónomo.",
                "Con el metrónomo a 60 BPM, toca cuatro tiempos de Em y cuatro de Am. Si llegas "
                "tarde al cambio, baja a 50 BPM: limpio primero, rápido después.",
            ),
        },
    ],
    "ejercicios": [
        {
            "leccion": 8,
            "nombre": "Cambio Em - Am",
            "descripcion": "Practica el cambio fluido entre estos dos acordes con el metrónomo.",
            "bpm": 60,
            "compas": "4/4",
            "duracion_min": 10,
            "acordes": ["Em", "Am"],
            "pasos": [
                "Coloca el metrónomo a 60 BPM.",
                "Toca el acorde Em durante 4 tiempos.",
                "Cambia a Am durante 4 tiempos.",
                "Repite el ciclo sin detenerte durante 2 minutos.",
                "Aumenta 10 BPM cuando lo sientas cómodo.",
            ],
        },
        {
            "leccion": 7,
            "nombre": "Am y Dm alternados",
            "descripcion": "Alterna Am y Dm cuidando que suenen solo las cuerdas correctas.",
            "bpm": 60,
            "compas": "4/4",
            "duracion_min": 8,
            "acordes": ["Am", "Dm"],
            "pasos": [
                "Forma Am y rasguea desde la 5.ª cuerda durante 4 tiempos.",
                "Cambia a Dm y rasguea desde la 4.ª cuerda durante 4 tiempos.",
                "Repite ocho veces revisando que no suenen las cuerdas marcadas con ×.",
                "Pasa a 2 tiempos por acorde cuando el cambio salga a tiempo.",
            ],
        },
    ],
    "evaluacion": [
        _pregunta(
            "¿Dónde se pisa el acorde Em?",
            [
                "5.ª y 4.ª cuerda en el traste 2",
                "3.ª y 2.ª cuerda en el traste 1",
                "6.ª cuerda en el traste 3",
                "1.ª y 2.ª cuerda en el traste 3",
            ],
            0,
        ),
        _pregunta(
            "En Am, ¿qué cuerda no se toca?",
            ["La 6.ª (Mi grave)", "La 1.ª (Mi agudo)", "La 3.ª", "Ninguna, suenan las seis"],
            0,
        ),
        _pregunta("¿Cuántas cuerdas suenan en Dm?", ["4", "6", "5", "3"], 0),
        _pregunta(
            "¿Qué tienen en común Em y Am?",
            [
                "Ambos pisan la 4.ª cuerda en el traste 2",
                "Ambos usan cejilla",
                "Ambos se tocan sin pisar ninguna cuerda",
                "Ambos son acordes mayores",
            ],
            0,
        ),
        _pregunta(
            "¿Qué carácter suelen transmitir los acordes menores?",
            [
                "Más serio o melancólico",
                "Más alegre y brillante",
                "Ninguno, suenan igual que los mayores",
                "Siempre suenan desafinados",
            ],
            0,
        ),
    ],
}

BLOQUE_MAYORES: Contenido = {
    "titulo": "Acordes mayores abiertos",
    "descripcion": "E, A, D, G y C: los acordes con los que se tocan cientos de canciones.",
    "nivel": "principiante",
    "lecciones": [
        {
            "titulo": "Los acordes E y A",
            "descripcion": "Mi mayor y La mayor, primos cercanos de Em y Am.",
            "duracion_min": 15,
            "acordes": ["E", "A"],
            "temas": ["Mi mayor", "La mayor", "mayor y menor"],
            "contenido": _p(
                "E (Mi mayor) es Em con un dedo más: añade el dedo 1 en la 3.ª cuerda, traste 1. "
                "Ese único cambio convierte el acorde menor en mayor.",
                "A (La mayor) pisa la 4.ª, 3.ª y 2.ª cuerda en el traste 2. Los tres dedos "
                "quedan muy juntos: colócalos en diagonal para que quepan. La 6.ª no se toca.",
                "Toca Em y luego E, Am y luego A. Escucha cómo el acorde mayor suena más "
                "brillante.",
            ),
        },
        {
            "titulo": "El acorde D",
            "descripcion": "Re mayor: forma de triángulo en las cuatro cuerdas agudas.",
            "duracion_min": 12,
            "acordes": ["D"],
            "temas": ["Re mayor", "forma de triángulo"],
            "contenido": _p(
                "D (Re mayor) se toca en las cuatro cuerdas agudas, con la 4.ª al aire. Pisa la "
                "3.ª cuerda en el traste 2 con el dedo 1, la 1.ª en el traste 2 con el dedo 2 y "
                "la 2.ª en el traste 3 con el dedo 3.",
                "Los dedos forman un triángulo. Cuida que el dedo 3 no apague la 1.ª cuerda.",
                "Como en Dm, rasguea desde la 4.ª cuerda.",
            ),
        },
        {
            "titulo": "Los acordes G y C",
            "descripcion": "Sol y Do mayor: dos acordes abiertos que se estiran por el mástil.",
            "duracion_min": 15,
            "acordes": ["G", "C"],
            "temas": ["Sol mayor", "Do mayor", "estirar la mano"],
            "contenido": _p(
                "G (Sol mayor) suena con las seis cuerdas: dedo 3 en la 6.ª cuerda, traste 3; "
                "dedo 2 en la 5.ª, traste 2; y dedo 4 en la 1.ª, traste 3.",
                "C (Do mayor) no toca la 6.ª cuerda: dedo 3 en la 5.ª, traste 3; dedo 2 en la "
                "4.ª, traste 2; y dedo 1 en la 2.ª, traste 1.",
                "Entre G y C los dedos viajan en bloque. Practica el cambio en silencio antes "
                "de rasguear.",
            ),
        },
    ],
    "ejercicios": [
        {
            "leccion": 11,
            "nombre": "Cambios G - C",
            "descripcion": "Cambia entre G y C manteniendo el pulso.",
            "bpm": 60,
            "compas": "4/4",
            "duracion_min": 8,
            "acordes": ["G", "C"],
            "pasos": [
                "Forma G y rasguea 4 tiempos.",
                "Cambia a C sin mirar la mano derecha y rasguea 4 tiempos.",
                "Repite el ciclo durante 2 minutos.",
                "Reduce a 2 tiempos por acorde cuando no pierdas el pulso.",
            ],
        },
        {
            "leccion": 10,
            "nombre": "Cambios rápidos G - D",
            "descripcion": "Un cambio muy común en canciones populares.",
            "bpm": 80,
            "compas": "4/4",
            "duracion_min": 8,
            "acordes": ["G", "D"],
            "pasos": [
                "Empieza a 60 BPM con 4 tiempos por acorde.",
                "Pasa a 2 tiempos por acorde.",
                "Sube 5 BPM cada vez que completes un minuto sin errores.",
                "Meta: 80 BPM con 2 tiempos por acorde.",
            ],
        },
    ],
    "evaluacion": [
        _pregunta(
            "¿Qué diferencia a E de Em?",
            [
                "E añade la 3.ª cuerda en el traste 1",
                "E se toca sin la 6.ª cuerda",
                "E usa cejilla",
                "No hay diferencia",
            ],
            0,
        ),
        _pregunta(
            "¿Cuántas cuerdas suenan en D?",
            ["4, desde la 4.ª cuerda", "6", "5, desde la 5.ª cuerda", "3"],
            0,
        ),
        _pregunta("En C, ¿qué cuerda no se toca?", ["La 6.ª", "La 5.ª", "La 1.ª", "La 2.ª"], 0),
        _pregunta(
            "¿Qué cuerdas se pisan en el traste 2 en el acorde A?",
            ["4.ª, 3.ª y 2.ª", "6.ª, 5.ª y 4.ª", "3.ª, 2.ª y 1.ª", "Solo la 5.ª"],
            0,
        ),
        _pregunta(
            "En G, ¿en qué traste se pisa la 6.ª cuerda?",
            ["Traste 3", "Traste 1", "Traste 2", "Se toca al aire"],
            0,
        ),
    ],
}

BLOQUE_RITMO: Contenido = {
    "titulo": "Ritmo y rasgueo",
    "descripcion": "Pulso, compás y los patrones de rasgueo que dan vida a los acordes.",
    "nivel": "principiante",
    "lecciones": [
        {
            "titulo": "Pulso, compás y metrónomo",
            "descripcion": "Qué es el BPM y cómo contar un compás de 4/4.",
            "duracion_min": 10,
            "acordes": [],
            "temas": ["pulso", "BPM", "compás de 4/4"],
            "contenido": _p(
                "El pulso es el latido regular de la música. El metrónomo lo marca en BPM: "
                "pulsos por minuto. A 60 BPM hay un pulso por segundo.",
                "El compás agrupa los pulsos. En 4/4 se cuenta «1, 2, 3, 4» y el 1 es el tiempo "
                "fuerte; el metrónomo suele marcarlo con un sonido distinto.",
                "Practica contando en voz alta con el metrónomo antes de tocar. Tocar a tiempo "
                "es más importante que tocar rápido.",
            ),
        },
        {
            "titulo": "Rasgueo abajo y arriba",
            "descripcion": "Golpes hacia abajo en los tiempos y hacia arriba en el «y».",
            "duracion_min": 12,
            "acordes": ["G", "Em"],
            "temas": ["golpe abajo", "golpe arriba", "corcheas"],
            "contenido": _p(
                "El golpe hacia abajo va en los tiempos (1, 2, 3, 4) y el golpe hacia arriba en "
                "el contratiempo, que se cuenta «y»: «1 y 2 y 3 y 4 y».",
                "Mueve la mano como un péndulo, desde la muñeca y sin parar: abajo en los "
                "números, arriba en las «y». Aunque no toques una cuerda, el movimiento sigue.",
                "Empieza solo con golpes hacia abajo en G y Em. Después añade los de arriba.",
            ),
        },
        {
            "titulo": "El patrón folk",
            "descripcion": "Abajo, abajo-arriba, arriba-abajo-arriba: el rasgueo más usado.",
            "duracion_min": 15,
            "acordes": ["G", "C", "D"],
            "temas": ["patrón folk", "D DU UDU", "síncopa"],
            "contenido": _p(
                "El patrón folk se escribe D DU UDU (D = abajo, U = arriba) y ocupa un compás "
                "de 4/4: «1, 2 y, y 4 y». En el tiempo 3 la mano baja sin tocar.",
                "Ese golpe en el aire crea la síncopa que hace sonar el patrón con movimiento. "
                "Mantén el péndulo aunque no toques.",
                "Practícalo primero con las cuerdas apagadas (la mano izquierda apoyada sin "
                "pisar) y luego sobre G, C y D.",
            ),
        },
        {
            "titulo": "Compás de 3/4: el vals",
            "descripcion": "Tres tiempos por compás, con el primero acentuado.",
            "duracion_min": 12,
            "acordes": ["C", "G"],
            "temas": ["compás de 3/4", "vals", "acento"],
            "contenido": _p(
                "En 3/4 cada compás tiene tres tiempos: «1, 2, 3». El 1 se acentúa y los otros "
                "dos son suaves. Es el compás del vals y de muchos pasillos.",
                "Un patrón sencillo: el 1 con un golpe fuerte hacia abajo en las cuerdas "
                "graves y el 2 y 3 con golpes suaves en las agudas.",
                "Configura el metrónomo en 3/4 para que marque el primer tiempo.",
            ),
        },
    ],
    "ejercicios": [
        {
            "leccion": 13,
            "nombre": "Rasgueo básico en 4/4",
            "descripcion": "Golpes abajo y arriba constantes sobre G y Em.",
            "bpm": 70,
            "compas": "4/4",
            "duracion_min": 8,
            "acordes": ["G", "Em"],
            "pasos": [
                "Cuenta «1 y 2 y 3 y 4 y» con el metrónomo.",
                "Rasguea solo hacia abajo en los números durante 4 compases de G.",
                "Añade los golpes hacia arriba en las «y».",
                "Cambia a Em cada 2 compases sin detener la mano derecha.",
            ],
        },
        {
            "leccion": 14,
            "nombre": "Patrón folk sobre G",
            "descripcion": "D DU UDU sobre un solo acorde hasta que salga automático.",
            "bpm": 70,
            "compas": "4/4",
            "duracion_min": 10,
            "acordes": ["G"],
            "pasos": [
                "Practica el patrón con las cuerdas apagadas a 60 BPM.",
                "Toca el patrón sobre G durante 8 compases.",
                "Verifica que en el tiempo 3 la mano baja sin tocar.",
                "Sube a 70 BPM cuando no pierdas el péndulo.",
            ],
        },
        {
            "leccion": 15,
            "nombre": "Vals en 3/4 con C y G",
            "descripcion": "Acento en el primer tiempo y dos golpes suaves.",
            "bpm": 80,
            "compas": "3/4",
            "duracion_min": 8,
            "acordes": ["C", "G"],
            "pasos": [
                "Configura el metrónomo en 3/4.",
                "Toca C: golpe fuerte en el 1, suaves en el 2 y el 3.",
                "Cambia a G cada 2 compases.",
                "Repite 16 compases sin perder el acento.",
            ],
        },
    ],
    "evaluacion": [
        _pregunta("¿Cuántos tiempos tiene un compás de 4/4?", ["4", "3", "2", "8"], 0),
        _pregunta(
            "¿Qué indica el BPM del metrónomo?",
            [
                "Los pulsos por minuto",
                "La cantidad de acordes",
                "Los compases de la canción",
                "El volumen",
            ],
            0,
        ),
        _pregunta(
            "En el rasgueo básico, ¿en qué dirección va el golpe en los tiempos 1, 2, 3 y 4?",
            ["Hacia abajo", "Hacia arriba", "No se toca", "Depende de la cuerda"],
            0,
        ),
        _pregunta("¿Cuántos tiempos tiene un compás de vals (3/4)?", ["3", "4", "2", "6"], 0),
        _pregunta(
            "Si un cambio de acorde no sale a tiempo con el metrónomo, ¿qué conviene hacer?",
            [
                "Bajar el BPM hasta tocarlo limpio y subir poco a poco",
                "Subir el BPM para practicar bajo presión",
                "Quitar el metrónomo",
                "Tocar más fuerte",
            ],
            0,
        ),
    ],
}

BLOQUE_PROGRESIONES: Contenido = {
    "titulo": "Progresiones y cambios fluidos",
    "descripcion": "Encadena acordes como en las canciones reales, sin pausas entre cambios.",
    "nivel": "intermedio",
    "lecciones": [
        {
            "titulo": "La progresión G - D - Em - C",
            "descripcion": "I - V - vi - IV: la progresión de cientos de canciones pop.",
            "duracion_min": 15,
            "acordes": ["G", "D", "Em", "C"],
            "temas": ["grados", "I - V - vi - IV", "tonalidad de G"],
            "contenido": _p(
                "En la tonalidad de Sol, los acordes G, D, Em y C son los grados I, V, vi y IV. "
                "Esa progresión aparece en una enorme cantidad de canciones.",
                "Toca un compás de cada acorde con el patrón folk. El cambio más difícil es de "
                "Em a C: prepara los dedos durante el último golpe hacia arriba.",
                "Cuando salga fluida, canta encima una melodía conocida que use esta progresión.",
            ),
        },
        {
            "titulo": "El dedo pivote",
            "descripcion": "Dedos que no se levantan para cambiar más rápido.",
            "duracion_min": 12,
            "acordes": ["C", "Am", "Em", "G"],
            "temas": ["dedo pivote", "economía de movimiento"],
            "contenido": _p(
                "Un dedo pivote es el que está en el mismo lugar en dos acordes seguidos: no se "
                "levanta, y los demás giran alrededor de él.",
                "Entre C y Am, los dedos 1 y 2 se quedan donde están y solo se mueve el 3. "
                "Entre Em y G, el dedo que pisa la 5.ª cuerda en el traste 2 puede quedarse.",
                "Busca dedos pivote en cada cambio que practiques: ahorran tiempo y esfuerzo.",
            ),
        },
        {
            "titulo": "Blues en A",
            "descripcion": "La forma de 12 compases con A, D y E.",
            "duracion_min": 15,
            "acordes": ["A", "D", "E"],
            "temas": ["blues de 12 compases", "I - IV - V"],
            "contenido": _p(
                "El blues clásico dura 12 compases y usa tres acordes: los grados I, IV y V. "
                "En La son A, D y E.",
                "La forma es: 4 compases de A, 2 de D, 2 de A, 1 de E, 1 de D, 1 de A y 1 de E "
                "para volver al inicio.",
                "Cuenta los compases en voz alta las primeras veces; la forma se memoriza "
                "tocándola.",
            ),
        },
    ],
    "ejercicios": [
        {
            "leccion": 16,
            "nombre": "Progresión G - D - Em - C",
            "descripcion": "Un compás por acorde con el patrón folk.",
            "bpm": 80,
            "compas": "4/4",
            "duracion_min": 10,
            "acordes": ["G", "D", "Em", "C"],
            "pasos": [
                "Empieza a 60 BPM con golpes solo hacia abajo.",
                "Toca un compás de cada acorde en orden.",
                "Repite la progresión cuatro veces sin parar.",
                "Cambia al patrón folk y sube hasta 80 BPM.",
            ],
        },
        {
            "leccion": 18,
            "nombre": "Blues en A de 12 compases",
            "descripcion": "Recorre la forma completa del blues sin perderte.",
            "bpm": 90,
            "compas": "4/4",
            "duracion_min": 10,
            "acordes": ["A", "D", "E"],
            "pasos": [
                "Toca 4 compases de A.",
                "Toca 2 compases de D y 2 de A.",
                "Toca 1 compás de E, 1 de D, 1 de A y 1 de E.",
                "Vuelve al inicio y repite la forma tres veces.",
            ],
        },
    ],
    "evaluacion": [
        _pregunta(
            "En la tonalidad de G, ¿qué grados son G - D - Em - C?",
            ["I - V - vi - IV", "I - IV - V - I", "ii - V - I - IV", "I - vi - ii - V"],
            0,
        ),
        _pregunta(
            "¿Qué es un dedo pivote?",
            [
                "Un dedo que no se levanta porque está en el mismo lugar en ambos acordes",
                "El dedo que hace la cejilla",
                "El pulgar detrás del mástil",
                "El dedo que pulsa la cuerda más grave",
            ],
            0,
        ),
        _pregunta(
            "¿Qué acordes forman el blues en A?",
            ["A, D y E", "A, C y G", "Am, Dm y Em", "A, B y C"],
            0,
        ),
        _pregunta(
            "¿Cuántos compases tiene la forma clásica del blues?",
            ["12", "8", "16", "4"],
            0,
        ),
        _pregunta("¿Qué acorde es el grado IV en la tonalidad de G?", ["C", "D", "Em", "A"], 0),
    ],
}

BLOQUE_CEJILLA: Contenido = {
    "titulo": "La cejilla",
    "descripcion": "F, Bm y los acordes menores con barra: el siguiente nivel de la guitarra.",
    "nivel": "intermedio",
    "lecciones": [
        {
            "titulo": "Qué es la cejilla y cómo practicarla",
            "descripcion": "Un dedo que pisa varias cuerdas a la vez, sin forzar la mano.",
            "duracion_min": 15,
            "acordes": [],
            "temas": ["cejilla", "peso del brazo", "pulgar"],
            "contenido": _p(
                "En la cejilla el dedo 1 pisa varias cuerdas en el mismo traste, como una "
                "cejuela móvil. Permite tocar el mismo acorde en distintas alturas del mástil.",
                "La fuerza no sale del pulgar: sale del peso del brazo que tira hacia atrás. "
                "Apoya el índice justo detrás del traste y gíralo un poco hacia su borde, "
                "que es más duro que la yema.",
                "Practica en el traste 5, donde las cuerdas están más bajas, y pulsa cada "
                "cuerda por separado. Descansa la mano cada pocos minutos.",
            ),
        },
        {
            "titulo": "El acorde F",
            "descripcion": "Fa mayor con cejilla completa en el traste 1.",
            "duracion_min": 15,
            "acordes": ["F"],
            "temas": ["Fa mayor", "cejilla completa", "forma de E"],
            "contenido": _p(
                "F (Fa mayor) es la forma de E desplazada al traste 1, con el dedo 1 haciendo "
                "la cejilla sobre las seis cuerdas.",
                "Coloca la cejilla y luego: dedo 2 en la 3.ª cuerda, traste 2; dedo 3 en la 5.ª, "
                "traste 3; y dedo 4 en la 4.ª, traste 3.",
                "Es el acorde que más cuesta al principio. Si una cuerda no suena, mueve el "
                "índice unos milímetros hasta encontrar la posición.",
            ),
        },
        {
            "titulo": "El acorde Bm",
            "descripcion": "Si menor con cejilla en el traste 2 desde la 5.ª cuerda.",
            "duracion_min": 15,
            "acordes": ["Bm"],
            "temas": ["Si menor", "forma de Am", "cejilla en el traste 2"],
            "contenido": _p(
                "Bm (Si menor) es la forma de Am desplazada al traste 2, con cejilla del dedo 1 "
                "desde la 5.ª cuerda. La 6.ª no se toca.",
                "Dedo 2 en la 2.ª cuerda, traste 3; dedos 3 y 4 en la 4.ª y la 3.ª, traste 4.",
                "Aparece en muchas canciones en Re y en Sol. Practica el cambio entre G y Bm.",
            ),
        },
        {
            "titulo": "Acordes menores con cejilla: Fm, Gm y Cm",
            "descripcion": "La misma forma, distinto traste: así se mueven los acordes.",
            "duracion_min": 20,
            "acordes": ["Fm", "Gm", "Cm"],
            "temas": ["formas móviles", "forma de Em", "forma de Am"],
            "contenido": _p(
                "Fm y Gm usan la forma de Em con cejilla: en el traste 1 suena Fm y en el "
                "traste 3, Gm. Con la misma forma recorres todo el mástil.",
                "Cm usa la forma de Am con cejilla en el traste 3, desde la 5.ª cuerda.",
                "Aprender formas móviles te da todos los acordes mayores y menores con solo "
                "cuatro posiciones.",
            ),
        },
    ],
    "ejercicios": [
        {
            "leccion": 19,
            "nombre": "Cejilla limpia nota por nota",
            "descripcion": "Revisa que cada cuerda suene bajo la cejilla.",
            "bpm": 50,
            "compas": "4/4",
            "duracion_min": 5,
            "acordes": [],
            "pasos": [
                "Haz cejilla con el dedo 1 en el traste 5.",
                "Pulsa cada cuerda, de la 6.ª a la 1.ª, una por tiempo.",
                "Si una cuerda suena apagada, ajusta el dedo y repite esa cuerda.",
                "Baja un traste cada vez que todas suenen limpias.",
            ],
        },
        {
            "leccion": 20,
            "nombre": "Cambio C - F",
            "descripcion": "Del acorde abierto a la cejilla sin perder tiempo.",
            "bpm": 60,
            "compas": "4/4",
            "duracion_min": 8,
            "acordes": ["C", "F"],
            "pasos": [
                "Toca C durante 4 tiempos.",
                "Cambia a F y mantén la cejilla 4 tiempos.",
                "Repite 8 veces y descansa la mano.",
                "Reduce a 2 tiempos por acorde.",
            ],
        },
        {
            "leccion": 20,
            "nombre": "Progresión Am - F - C - G",
            "descripcion": "vi - IV - I - V en Do, con F en cejilla.",
            "bpm": 70,
            "compas": "4/4",
            "duracion_min": 10,
            "acordes": ["Am", "F", "C", "G"],
            "pasos": [
                "Empieza a 60 BPM con un compás por acorde.",
                "Usa golpes hacia abajo hasta que el cambio a F sea limpio.",
                "Cambia al patrón folk.",
                "Sube a 70 BPM.",
            ],
        },
    ],
    "evaluacion": [
        _pregunta(
            "¿Qué dedo hace normalmente la cejilla?",
            ["El índice (1)", "El medio (2)", "El anular (3)", "El pulgar"],
            0,
        ),
        _pregunta(
            "¿De dónde sale la fuerza para una cejilla limpia?",
            [
                "Del peso del brazo, con el índice justo detrás del traste",
                "De apretar el pulgar lo más fuerte posible",
                "De colocar el dedo en medio de dos trastes",
                "De rasguear más suave",
            ],
            0,
        ),
        _pregunta("¿En qué traste se hace la cejilla de F?", ["1", "2", "3", "5"], 0),
        _pregunta("¿En qué traste se hace la cejilla de Bm?", ["2", "1", "3", "4"], 0),
        _pregunta(
            "¿Qué forma de acorde abierto usan Fm y Gm con cejilla?",
            ["La de Em", "La de Am", "La de D", "La de C"],
            0,
        ),
    ],
}

BLOQUES: list[Contenido] = [
    BLOQUE_FUNDAMENTOS,
    BLOQUE_MENORES,
    BLOQUE_MAYORES,
    BLOQUE_RITMO,
    BLOQUE_PROGRESIONES,
    BLOQUE_CEJILLA,
]
