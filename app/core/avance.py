# =========================================================
# Estado y porcentaje de avance (HU-B-502, decisiones de la fase 5 §2). Funciones puras: el
# backend calcula el estado UNA vez y el frontend lo muestra tal cual, para que tarjetas, filtros
# y graficos coincidan entre pantallas.
# =========================================================
from typing import Literal

SIN_INICIAR = "sin_iniciar"
EN_CURSO = "en_curso"
FINALIZADO = "finalizado"
ESTADOS_DE_AVANCE = (SIN_INICIAR, EN_CURSO, FINALIZADO)
EstadoDeAvance = Literal["sin_iniciar", "en_curso", "finalizado"]

_CIEN = 100


def porcentaje(hechos: int, total: int) -> int:
    """Entero de 0 a 100 (0 si no hay nada). .5 sube, como round() de SQL."""
    if total <= 0:
        return 0
    return min(_CIEN, int(hechos * _CIEN / total + 0.5))


def estado_de_avance(*, hay_registro: bool, completo: bool) -> EstadoDeAvance:
    """sin_iniciar: ningun registro. finalizado: todo lo que lo compone esta completado.
    en_curso: lo demas (hay registro y falta algo)."""
    if completo:
        return FINALIZADO
    return EN_CURSO if hay_registro else SIN_INICIAR


def curso_completo(
    *,
    lecciones_total: int,
    lecciones_completadas: int,
    bloques_con_evaluacion: int,
    bloques_aprobados: int,
) -> bool:
    """Un curso se finaliza con todas las lecciones de su ruta completadas y las evaluaciones de
    sus bloques aprobadas. Un curso sin lecciones nunca esta finalizado."""
    return (
        lecciones_total > 0
        and lecciones_completadas >= lecciones_total
        and bloques_aprobados >= bloques_con_evaluacion
    )
