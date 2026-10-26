# =========================================================
# Cursos (HU-B-307 / HU-B-310). Toda verificacion "este curso es del
# docente" pasa por _curso_propio (404 si no lo es; el admin ve todo).
# =========================================================
import secrets
from typing import Any, Protocol

from sqlalchemy.exc import IntegrityError

from app.core.avance import curso_completo, estado_de_avance, porcentaje
from app.core.constants import ALFABETO_CODIGO, LARGO_CODIGO, ROL_ADMIN
from app.core.errors import Conflicto, NoEncontrado, ReglaNegocio
from app.core.privacidad import enmascarar_email
from app.core.security import CurrentUser
from app.repositories.base import AbrirSesion, Fila, RepositorioCursos
from app.schemas.curso import CursoCreate, RutaCursoIn

INTENTOS_CODIGO = 5
MENSAJE_CODIGO_INVALIDO = (
    "El código no existe o el curso ya cerró. Pídele a tu docente un código nuevo."
)
MENSAJE_ARCHIVADO = "El curso está archivado: no admite cambios."
MENSAJE_CURSO_NO_DISPONIBLE = "Ese curso ya tiene docente o dejó de estar disponible."
ORDENES_MIS_CURSOS = ("ultimo_avance", "nombre", "avance")


def curso_con_avance(curso: Fila, conteos: Fila) -> Fila:
    """El curso del estudiante con su avance y estado (HU-B-502). Funcion pura: los conteos vienen
    de una sola consulta y el porcentaje usa las lecciones de la ruta del curso, igual que el panel
    del docente (HU-B-310 y HU-B-408)."""
    lecciones = (conteos.get("lecciones_completadas", 0), conteos.get("lecciones_total", 0))
    ultimo = conteos.get("ultimo_avance")
    completo = curso_completo(
        lecciones_total=lecciones[1],
        lecciones_completadas=lecciones[0],
        bloques_con_evaluacion=conteos.get("bloques_con_evaluacion", 0),
        bloques_aprobados=conteos.get("bloques_aprobados", 0),
    )
    return {
        **curso,
        "docente": {"nombre": curso["docente_nombre"], "apellido": curso.get("docente_apellido")},
        "avance": {
            "pct": porcentaje(*lecciones),
            "lecciones": {"completadas": lecciones[0], "total": lecciones[1]},
            "ejercicios": {
                "completados": conteos.get("ejercicios_completados", 0),
                "total": conteos.get("ejercicios_total", 0),
            },
            "bloques_aprobados": conteos.get("bloques_aprobados", 0),
            "bloques_total": conteos.get("bloques_total", 0),
        },
        "estado": estado_de_avance(hay_registro=ultimo is not None, completo=completo),
        "ultimo_avance": ultimo,
    }


def _ordenar_mis_cursos(cursos: list[Fila], orden: str) -> list[Fila]:
    por_nombre = sorted(cursos, key=lambda c: c["nombre"].casefold())
    if orden == "nombre":
        return por_nombre
    if orden == "avance":
        return sorted(por_nombre, key=lambda c: c["avance"]["pct"], reverse=True)
    # El ultimo avance mas reciente primero; sin avances al final (el texto ISO ordena como fecha).
    con = sorted((c for c in por_nombre if c["ultimo_avance"]), key=lambda c: c["ultimo_avance"])
    sin = [c for c in por_nombre if not c["ultimo_avance"]]
    return con[::-1] + sin


def generar_codigo() -> str:
    """8 caracteres sin ambiguedades (sin 0/O/1/I/L), con un generador criptografico."""
    return "".join(secrets.choice(ALFABETO_CODIGO) for _ in range(LARGO_CODIGO))


class RepositorioSeguimiento(Protocol):
    def estudiantes(
        self,
        sesion: Any,
        curso_id: int,
        *,
        q: str | None,
        orden: str,
        pagina: int,
        por_pagina: int,
    ) -> tuple[list[Fila], int]: ...
    def inscripcion(self, sesion: Any, curso_id: int, estudiante_id: str) -> Fila | None: ...
    def ejercicios_de_lecciones(
        self, sesion: Any, leccion_ids: list[int], estudiante_id: str
    ) -> list[Fila]: ...
    def intentos_del_estudiante(
        self, sesion: Any, curso_id: int, estudiante_id: str
    ) -> list[Fila]: ...
    def retroalimentaciones(self, sesion: Any, curso_id: int, estudiante_id: str) -> list[Fila]: ...
    def resumen(self, sesion: Any, docente_id: str | None) -> Fila: ...


class RutaDeEstudiante(Protocol):
    def ruta_de_estudiante(
        self, sesion: Any, usuario_id: str | None, curso_id: int | None
    ) -> list[Fila]: ...


def _sin_email(fila: Fila) -> Fila:
    """El docente nunca recibe el correo completo del estudiante."""
    return {**fila, "email": enmascarar_email(fila.get("email"))}


class CursoService:
    def __init__(
        self,
        abrir_sesion: AbrirSesion,
        cursos: RepositorioCursos,
        seguimiento: RepositorioSeguimiento | None = None,
        ruta: RutaDeEstudiante | None = None,
    ) -> None:
        self._abrir_sesion = abrir_sesion
        self._cursos = cursos
        self._seguimiento = seguimiento
        self._ruta = ruta

    # --- Docente: cursos --------------------------------------------------------
    def listar_de_docente(self, usuario: CurrentUser, *, archivados: bool) -> list[Fila]:
        docente = None if usuario.rol == ROL_ADMIN else usuario.id
        with self._abrir_sesion() as sesion:
            return self._cursos.listar_de_docente(sesion, docente, archivados=archivados)

    def detalle(self, usuario: CurrentUser, curso_id: int) -> Fila:
        with self._abrir_sesion() as sesion:
            curso = self._curso_propio(sesion, usuario, curso_id)
            return {
                **curso,
                "ruta": self._cursos.ruta(sesion, curso_id),
                "estudiantes": self._cursos.contar_estudiantes(sesion, curso_id),
            }

    def crear(self, docente: CurrentUser, datos: CursoCreate) -> Fila:
        """Crea el curso con un codigo de invitacion unico (reintenta si colisiona)."""
        with self._abrir_sesion() as sesion:
            for _ in range(INTENTOS_CODIGO):
                fila = {
                    **datos.model_dump(),
                    "docente_id": docente.id,
                    "codigo_invitacion": generar_codigo(),
                }
                try:
                    with sesion.begin_nested():  # savepoint: una colision no aborta la transaccion
                        return self._cursos.crear(sesion, fila)
                except IntegrityError:
                    continue
        raise ReglaNegocio("No se pudo generar un código de invitación. Inténtalo de nuevo.")

    # --- Docente: cursos disponibles (HU-B-413) ----------------------------------
    def disponibles(self) -> list[Fila]:
        with self._abrir_sesion() as sesion:
            return self._cursos.listar_disponibles(sesion)

    def asignarse(self, docente: CurrentUser, curso_id: int) -> Fila:
        """Toma un curso activo que no tiene docente. 409 si otro se adelantó."""
        with self._abrir_sesion() as sesion:
            curso = self._cursos.obtener(sesion, curso_id)
            if curso is None:
                raise NoEncontrado(f"No existe el curso {curso_id}")
            asignado = self._cursos.asignar_docente(sesion, curso_id, docente.id)
            if asignado is None:
                raise Conflicto(MENSAJE_CURSO_NO_DISPONIBLE)
            return asignado

    def retirarse(self, docente: CurrentUser, curso_id: int) -> Fila:
        """Deja el curso sin docente: sus estudiantes y su ruta se conservan."""
        with self._abrir_sesion() as sesion:
            curso = self._cursos.quitar_docente(sesion, curso_id, docente.id)
            if curso is None:
                raise NoEncontrado(f"No existe el curso {curso_id}")
            return curso

    def actualizar(self, usuario: CurrentUser, curso_id: int, cambios: Fila) -> Fila:
        with self._abrir_sesion() as sesion:
            self._curso_propio(sesion, usuario, curso_id, bloquear=True, activo=True)
            return self._cursos.actualizar(sesion, curso_id, cambios)

    def regenerar_codigo(self, usuario: CurrentUser, curso_id: int) -> Fila:
        """Los estudiantes ya inscritos siguen en el curso; el codigo anterior deja de servir."""
        with self._abrir_sesion() as sesion:
            self._curso_propio(sesion, usuario, curso_id, bloquear=True, activo=True)
            for _ in range(INTENTOS_CODIGO):
                try:
                    with sesion.begin_nested():
                        return self._cursos.actualizar(
                            sesion, curso_id, {"codigo_invitacion": generar_codigo()}
                        )
                except IntegrityError:
                    continue
        raise ReglaNegocio("No se pudo generar un código de invitación. Inténtalo de nuevo.")

    def archivar(self, usuario: CurrentUser, curso_id: int) -> Fila:
        """Soft delete: el curso y su historial se conservan."""
        with self._abrir_sesion() as sesion:
            self._curso_propio(sesion, usuario, curso_id, bloquear=True)
            return self._cursos.archivar(sesion, curso_id)

    def definir_ruta(self, usuario: CurrentUser, curso_id: int, ruta: RutaCursoIn) -> list[Fila]:
        """Reemplaza la ruta del curso en una sola transaccion (todo o nada)."""
        pedidos = {b.bloque_id for b in ruta.bloques}
        with self._abrir_sesion() as sesion:
            self._curso_propio(sesion, usuario, curso_id, bloquear=True, activo=True)
            faltantes = pedidos - self._cursos.bloques_publicados(sesion, pedidos)
            if faltantes:
                raise ReglaNegocio(
                    f"Estos bloques no existen o no están publicados: {sorted(faltantes)}"
                )
            self._cursos.reemplazar_ruta(
                sesion, curso_id, [(b.bloque_id, b.orden) for b in ruta.bloques]
            )
        return [b.model_dump() for b in sorted(ruta.bloques, key=lambda b: b.orden)]

    # --- Docente: estudiantes ---------------------------------------------------
    def estudiantes(
        self, usuario: CurrentUser, curso_id: int, filtros: dict[str, Any]
    ) -> tuple[list[Fila], int]:
        with self._abrir_sesion() as sesion:
            self._curso_propio(sesion, usuario, curso_id)
            filas, total = self._seguimiento.estudiantes(sesion, curso_id, **filtros)
        return [_sin_email(f) for f in filas], total

    def detalle_estudiante(self, usuario: CurrentUser, curso_id: int, estudiante_id: str) -> Fila:
        """Progreso por bloque -> leccion/ejercicio, intentos y comentarios (consultas fijas)."""
        with self._abrir_sesion() as sesion:
            self._curso_propio(sesion, usuario, curso_id)
            inscrito = self._inscrito(sesion, curso_id, estudiante_id)
            ruta = self._ruta.ruta_de_estudiante(sesion, estudiante_id, curso_id)
            leccion_ids = [lec["id"] for b in ruta for lec in b["lecciones"]]
            ejercicios = self._seguimiento.ejercicios_de_lecciones(
                sesion, leccion_ids, estudiante_id
            )
            intentos = self._seguimiento.intentos_del_estudiante(sesion, curso_id, estudiante_id)
            comentarios = self._seguimiento.retroalimentaciones(sesion, curso_id, estudiante_id)
        for bloque in ruta:
            for leccion in bloque["lecciones"]:
                leccion["ejercicios"] = [e for e in ejercicios if e["leccion_id"] == leccion["id"]]
            bloque["intentos"] = [i for i in intentos if i["bloque_id"] == bloque["id"]]
        return {
            **_sin_email(inscrito),
            "curso_id": curso_id,
            "bloques": ruta,
            "intentos_del_curso": [i for i in intentos if i["bloque_id"] is None],
            "retroalimentaciones": comentarios,
        }

    def retirar(self, usuario: CurrentUser, curso_id: int, estudiante_id: str) -> None:
        with self._abrir_sesion() as sesion:
            self._curso_propio(sesion, usuario, curso_id, bloquear=True)
            if not self._cursos.retirar(sesion, curso_id, estudiante_id):
                raise NoEncontrado("Ese estudiante no está inscrito en el curso.")

    def comentar(
        self, usuario: CurrentUser, curso_id: int, estudiante_id: str, mensaje: str
    ) -> Fila:
        with self._abrir_sesion() as sesion:
            self._curso_propio(sesion, usuario, curso_id, activo=True)
            self._inscrito(sesion, curso_id, estudiante_id)
            return self._cursos.crear_retroalimentacion(
                sesion,
                {
                    "curso_id": curso_id,
                    "estudiante_id": estudiante_id,
                    "docente_id": usuario.id,
                    "mensaje": mensaje,
                },
            )

    def resumen(self, usuario: CurrentUser) -> Fila:
        docente = None if usuario.rol == ROL_ADMIN else usuario.id
        with self._abrir_sesion() as sesion:
            return self._seguimiento.resumen(sesion, docente)

    # --- Estudiante -------------------------------------------------------------
    def unirse(self, estudiante_id: str, codigo: str) -> dict[str, Any]:
        """Idempotente: si ya estaba inscrito, responde igual."""
        with self._abrir_sesion() as sesion:
            curso = self._cursos.obtener_activo_por_codigo(sesion, codigo)
            if curso is None:
                raise NoEncontrado(MENSAJE_CODIGO_INVALIDO)
            self._cursos.inscribir(sesion, curso["id"], estudiante_id)
            mis_cursos = self._mis_cursos_con_avance(sesion, estudiante_id)
        return next(c for c in mis_cursos if c["id"] == curso["id"])

    def _mis_cursos_con_avance(self, sesion: Any, estudiante_id: str) -> list[Fila]:
        cursos = self._cursos.cursos_de_estudiante(sesion, estudiante_id)
        avance = self._cursos.avance_de_cursos(sesion, estudiante_id)
        return [curso_con_avance(c, avance.get(c["id"], {})) for c in cursos]

    def mis_cursos(
        self, estudiante_id: str, *, estado: str | None = None, orden: str = "ultimo_avance"
    ) -> list[Fila]:
        """Mis cursos activos con su avance y estado; `estado` filtra y `orden` ordena."""
        with self._abrir_sesion() as sesion:
            cursos = self._mis_cursos_con_avance(sesion, estudiante_id)
        if estado is not None:
            cursos = [c for c in cursos if c["estado"] == estado]
        return _ordenar_mis_cursos(cursos, orden)

    def mis_retroalimentaciones(self, estudiante_id: str, curso_id: int) -> list[Fila]:
        """Comentarios del docente para el estudiante; al leerlos quedan marcados (leida_en).
        `nueva` indica cuales no habia leido antes de esta consulta."""
        with self._abrir_sesion() as sesion:
            if self._seguimiento.inscripcion(sesion, curso_id, estudiante_id) is None:
                raise NoEncontrado(f"No existe el curso {curso_id}")
            comentarios = self._seguimiento.retroalimentaciones(sesion, curso_id, estudiante_id)
            self._cursos.marcar_leidas(sesion, curso_id, estudiante_id)
        return [{**c, "nueva": c["leida_en"] is None} for c in comentarios]

    def curso_propio(
        self, sesion: Any, usuario: CurrentUser, curso_id: int, *, activo: bool = False
    ) -> Fila:
        """Para otros servicios (evaluaciones del docente) dentro de su transaccion."""
        return self._curso_propio(sesion, usuario, curso_id, activo=activo)

    # --- Privados ---------------------------------------------------------------
    def _curso_propio(
        self,
        sesion: Any,
        usuario: CurrentUser,
        curso_id: int,
        *,
        bloquear: bool = False,
        activo: bool = False,
    ) -> Fila:
        """Un curso ajeno responde 404 (no 403) para no revelar que existe.
        El administrador puede operar cualquier curso."""
        curso = self._cursos.obtener(sesion, curso_id, bloquear=bloquear)
        es_suyo = curso is not None and (
            curso["docente_id"] == usuario.id or usuario.rol == ROL_ADMIN
        )
        if not es_suyo:
            raise NoEncontrado(f"No existe el curso {curso_id}")
        if activo and curso["archivado_en"] is not None:
            raise ReglaNegocio(MENSAJE_ARCHIVADO)
        return curso

    def _inscrito(self, sesion: Any, curso_id: int, estudiante_id: str) -> Fila:
        fila = self._seguimiento.inscripcion(sesion, curso_id, estudiante_id)
        if fila is None:
            raise NoEncontrado("Ese estudiante no está inscrito en el curso.")
        return fila
