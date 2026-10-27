# =========================================================
# Panel de progreso del docente (HU-B-408): como van sus estudiantes en TODOS sus cursos,
# bloque por bloque. Alcance: el docente solo ve sus cursos activos y a sus estudiantes; el
# administrador ve todos (o los de un docente). Un curso ajeno responde 404, no 403.
# No expone correos. La regla de desbloqueo de bloques es la UNICA de la ruta
# (ruta_service.estados_de_bloques): la matriz muestra exactamente lo que ve el estudiante.
# =========================================================
from typing import Any, Protocol

from app.core.avance import EN_CURSO, FINALIZADO, SIN_INICIAR, estado_de_avance
from app.core.constants import ROL_ADMIN
from app.core.errors import NoEncontrado
from app.core.security import CurrentUser
from app.repositories.base import AbrirSesion, Fila
from app.services.curso_service import CursoService, RepositorioSeguimiento
from app.services.ruta_service import RepositorioRuta, estados_de_bloques

MAXIMO_NECESITAN_APOYO = 20

MOTIVO_SIN_ACTIVIDAD = "sin_actividad"
MOTIVO_REPROBO_BLOQUE = "reprobo_bloque"

TRAMOS_DE_AVANCE = 5
ANCHO_DEL_TRAMO = 100 // TRAMOS_DE_AVANCE


class RepositorioProgresoDocente(Protocol):
    def resumen_cursos(
        self, sesion: Any, docente_id: str | None, curso_id: int | None
    ) -> list[Fila]: ...
    def bloques_por_curso(
        self, sesion: Any, docente_id: str | None, curso_id: int | None
    ) -> list[Fila]: ...
    def necesitan_apoyo(
        self, sesion: Any, docente_id: str | None, curso_id: int | None, limite: int
    ) -> list[Fila]: ...
    def celdas(
        self, sesion: Any, estudiante_ids: list[str], bloque_ids: list[int]
    ) -> list[Fila]: ...
    def cursos_del_estudiante(
        self, sesion: Any, docente_id: str | None, estudiante_id: str
    ) -> list[int]: ...
    def avance_de_la_seleccion(self, sesion: Any, filtros: Fila) -> list[Fila]: ...
    def actividad_por_dia(self, sesion: Any, filtros: Fila, dias: int) -> list[Fila]: ...
    def evaluaciones(self, sesion: Any, filtros: Fila) -> list[Fila]: ...


def _bloque(fila: Fila) -> Fila:
    """Una fila del agregado por bloque, con la pregunta mas fallada como objeto (o None)."""
    pregunta = fila["pregunta_mas_fallada"]
    return {
        "bloque_id": fila["bloque_id"],
        "numero": fila["numero"],
        "titulo": fila["titulo"],
        "orden": fila["orden"],
        "aprobados": fila["aprobados"],
        "intentos": fila["intentos"],
        "promedio_mejor_puntaje": fila["promedio_mejor_puntaje"],
        "pregunta_mas_fallada": (
            {"enunciado": pregunta, "fallos": fila["fallos_de_la_pregunta"]} if pregunta else None
        ),
    }


def _necesita_apoyo(fila: Fila) -> Fila:
    """Los motivos van como codigos; el frontend arma el texto de la lista."""
    motivos = []
    if fila["bloque_reprobado_id"] is not None:
        motivos.append(MOTIVO_REPROBO_BLOQUE)
    if fila["sin_actividad"]:
        motivos.append(MOTIVO_SIN_ACTIVIDAD)
    reprobado = None
    if fila["bloque_reprobado_id"] is not None:
        reprobado = {
            "bloque_id": fila["bloque_reprobado_id"],
            "titulo": fila["bloque_reprobado"],
            "intentos_reprobados": fila["intentos_reprobados"],
        }
    return {
        "estudiante_id": fila["estudiante_id"],
        "nombre": fila["nombre"],
        "apellido": fila["apellido"],
        "curso_id": fila["curso_id"],
        "curso": fila["curso"],
        "ultimo_avance": fila["ultimo_avance"],
        "motivos": motivos,
        "bloque_reprobado": reprobado,
    }


def _distribucion(grupos: list[Fila]) -> tuple[list[Fila], dict[str, int]]:
    """Cinco tramos de 20 % (0-19 ... 80-100) y el conteo por estado, de los mismos grupos: asi
    la suma de ambos siempre coincide. El estado sale de app/core/avance (decisiones fase 5 §2)."""
    tramos = [0] * TRAMOS_DE_AVANCE
    estados = {SIN_INICIAR: 0, EN_CURSO: 0, FINALIZADO: 0}
    for g in grupos:
        tramos[g["tramo"]] += g["estudiantes"]
        estado = estado_de_avance(hay_registro=g["hay_registro"], completo=g["completo"])
        estados[estado] += g["estudiantes"]
    distribucion = [
        {
            "desde": i * ANCHO_DEL_TRAMO,
            "hasta": 100 if i == TRAMOS_DE_AVANCE - 1 else (i + 1) * ANCHO_DEL_TRAMO - 1,
            "estudiantes": cantidad,
        }
        for i, cantidad in enumerate(tramos)
    ]
    return distribucion, estados


def _sin_correo(fila: Fila) -> Fila:
    return {k: v for k, v in fila.items() if k != "email"}


class ProgresoDocenteService:
    def __init__(  # noqa: PLR0913, PLR0917 - dependencias inyectadas desde app/container.py
        self,
        abrir_sesion: AbrirSesion,
        progreso: RepositorioProgresoDocente,
        ruta: RepositorioRuta,
        seguimiento: RepositorioSeguimiento,
        cursos: CursoService,
    ) -> None:
        self._abrir_sesion = abrir_sesion
        self._progreso = progreso
        self._ruta = ruta
        self._seguimiento = seguimiento
        self._cursos = cursos

    @staticmethod
    def _alcance(usuario: CurrentUser, docente_id: str | None = None) -> str | None:
        """None = todos los cursos (administrador). Un docente solo ve los suyos: el
        parametro docente_id lo ignora."""
        if usuario.rol == ROL_ADMIN:
            return docente_id
        return usuario.id

    def resumen(
        self, usuario: CurrentUser, curso_id: int | None, docente_id: str | None = None
    ) -> dict[str, Any]:
        docente = self._alcance(usuario, docente_id)
        with self._abrir_sesion() as sesion:
            cursos = self._progreso.resumen_cursos(sesion, docente, curso_id)
            if curso_id is not None and not cursos:
                raise NoEncontrado(f"No existe el curso {curso_id}")
            bloques = self._progreso.bloques_por_curso(sesion, docente, curso_id)
            apoyo = self._progreso.necesitan_apoyo(
                sesion, docente, curso_id, MAXIMO_NECESITAN_APOYO
            )
        por_curso: dict[int, list[Fila]] = {c["id"]: [] for c in cursos}
        for fila in bloques:
            por_curso[fila["curso_id"]].append(_bloque(fila))
        return {
            "cursos": [{**c, "bloques": por_curso[c["id"]]} for c in cursos],
            "necesitan_apoyo": [_necesita_apoyo(f) for f in apoyo],
        }

    def series(self, usuario: CurrentUser, filtros: dict[str, Any]) -> dict[str, Any]:
        """Series para las graficas del panel: actividad por dia, distribucion del avance,
        estados y evaluaciones. Todas salen del mismo alcance y filtros que /docente/progreso."""
        curso_id = filtros["curso_id"]
        consulta = {
            "docente_id": self._alcance(usuario, filtros["docente_id"]),
            "curso_id": curso_id,
            "bloque_id": filtros["bloque_id"],
            "estudiantes": filtros["estudiantes"],
        }
        with self._abrir_sesion() as sesion:
            if curso_id is not None:
                self._cursos.curso_propio(sesion, usuario, curso_id, activo=True)  # 404 si es ajeno
            grupos = self._progreso.avance_de_la_seleccion(sesion, consulta)
            actividad = [
                # AAAA-MM-DD: Flask serializa un date como "Mon, 19 Oct 2026 00:00:00 GMT".
                {**dia, "fecha": dia["fecha"].isoformat()}
                for dia in self._progreso.actividad_por_dia(sesion, consulta, filtros["dias"])
            ]
            evaluaciones = self._progreso.evaluaciones(sesion, consulta)
        distribucion, estados = _distribucion(grupos)
        return {
            "actividad_por_dia": actividad,
            "distribucion_avance": distribucion,
            "estados": estados,
            "evaluaciones": evaluaciones,
        }

    def matriz(
        self, usuario: CurrentUser, curso_id: int, filtros: dict[str, Any]
    ) -> tuple[list[Fila], int, list[Fila]]:
        """Estudiantes de una pagina x bloques de la ruta del curso. Devuelve
        (filas, total, encabezado de bloques)."""
        with self._abrir_sesion() as sesion:
            self._cursos.curso_propio(sesion, usuario, curso_id)  # 404 si es ajeno
            estudiantes, total = self._seguimiento.estudiantes(sesion, curso_id, **filtros)
            bloques = self._ruta.bloques(sesion, curso_id)
            ids = [b["id"] for b in bloques]
            con_evaluacion = set(self._ruta.evaluaciones_de_bloques(sesion, ids))
            celdas = (
                self._progreso.celdas(sesion, [e["estudiante_id"] for e in estudiantes], ids)
                if estudiantes and ids
                else []
            )
        por_estudiante: dict[str, dict[int, Fila]] = {}
        for celda in celdas:
            por_estudiante.setdefault(celda["estudiante_id"], {})[celda["bloque_id"]] = celda
        filas = [self._fila_de_matriz(e, ids, con_evaluacion, por_estudiante) for e in estudiantes]
        encabezado = [
            {"bloque_id": b["id"], "numero": b["numero"], "titulo": b["titulo"], "orden": i}
            for i, b in enumerate(bloques, start=1)
        ]
        return filas, total, encabezado

    @staticmethod
    def _fila_de_matriz(
        estudiante: Fila,
        bloque_ids: list[int],
        con_evaluacion: set[int],
        celdas: dict[str, dict[int, Fila]],
    ) -> Fila:
        propias = celdas.get(estudiante["estudiante_id"], {})
        aprobados = {b for b, c in propias.items() if c["aprobado"]}
        estados = estados_de_bloques(bloque_ids, con_evaluacion, aprobados)
        return {
            "estudiante_id": estudiante["estudiante_id"],
            "nombre": estudiante["nombre"],
            "apellido": estudiante["apellido"],
            "avance_pct": estudiante["avance_pct"],
            "ultimo_avance": estudiante["ultimo_avance"],
            "bloques": [
                {
                    "bloque_id": b,
                    "estado": estados[b],
                    "mejor_puntaje": propias.get(b, {}).get("mejor_puntaje"),
                    "intentos": propias.get(b, {}).get("intentos", 0),
                }
                for b in bloque_ids
            ],
        }

    def estudiante(
        self, usuario: CurrentUser, estudiante_id: str, docente_id: str | None = None
    ) -> dict[str, Any]:
        """Progreso de un estudiante en TODOS los cursos activos del docente donde esta inscrito."""
        docente = self._alcance(usuario, docente_id)
        with self._abrir_sesion() as sesion:
            cursos = self._progreso.cursos_del_estudiante(sesion, docente, estudiante_id)
        if not cursos:
            raise NoEncontrado("Ese estudiante no está inscrito en ninguno de tus cursos.")
        detalles = [
            _sin_correo(self._cursos.detalle_estudiante(usuario, c, estudiante_id)) for c in cursos
        ]
        primero = detalles[0]
        return {
            "estudiante_id": estudiante_id,
            "nombre": primero["nombre"],
            "apellido": primero.get("apellido"),
            "cursos": [
                {k: v for k, v in d.items() if k not in {"estudiante_id", "nombre", "apellido"}}
                for d in detalles
            ],
        }
