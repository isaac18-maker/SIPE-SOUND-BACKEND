import secrets
from typing import Any

from sqlalchemy.exc import IntegrityError

from app.core.constants import ALFABETO_CODIGO, LARGO_CODIGO, ROL_ADMIN
from app.core.errors import NoEncontrado, ReglaNegocio
from app.core.security import CurrentUser
from app.repositories.base import AbrirSesion, Fila, RepositorioCursos
from app.schemas.curso import CursoCreate, RutaCursoIn

INTENTOS_CODIGO = 5
MENSAJE_CODIGO_INVALIDO = (
    "El código no existe o el curso ya cerró. Pídele a tu docente un código nuevo."
)


def generar_codigo() -> str:
    """8 caracteres sin ambiguedades (sin 0/O/1/I/L), con un generador criptografico."""
    return "".join(secrets.choice(ALFABETO_CODIGO) for _ in range(LARGO_CODIGO))


class CursoService:
    def __init__(self, abrir_sesion: AbrirSesion, cursos: RepositorioCursos) -> None:
        self._abrir_sesion = abrir_sesion
        self._cursos = cursos

    # --- Docente (endpoints en HU-B-310) -------------------------------------
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

    def archivar(self, usuario: CurrentUser, curso_id: int) -> Fila:
        """Soft delete: el curso y su historial se conservan."""
        with self._abrir_sesion() as sesion:
            self._curso_propio(sesion, usuario, curso_id, bloquear=True)
            return self._cursos.archivar(sesion, curso_id)

    def definir_ruta(self, usuario: CurrentUser, curso_id: int, ruta: RutaCursoIn) -> list[Fila]:
        """Reemplaza la ruta del curso en una sola transaccion (todo o nada)."""
        pedidos = {b.bloque_id for b in ruta.bloques}
        with self._abrir_sesion() as sesion:
            self._curso_propio(sesion, usuario, curso_id, bloquear=True)
            faltantes = pedidos - self._cursos.bloques_publicados(sesion, pedidos)
            if faltantes:
                raise ReglaNegocio(
                    f"Estos bloques no existen o no están publicados: {sorted(faltantes)}"
                )
            self._cursos.reemplazar_ruta(
                sesion, curso_id, [(b.bloque_id, b.orden) for b in ruta.bloques]
            )
        return [b.model_dump() for b in sorted(ruta.bloques, key=lambda b: b.orden)]

    # --- Estudiante -------------------------------------------------------------
    def unirse(self, estudiante_id: str, codigo: str) -> dict[str, Any]:
        """Idempotente: si ya estaba inscrito, responde igual."""
        with self._abrir_sesion() as sesion:
            curso = self._cursos.obtener_activo_por_codigo(sesion, codigo)
            if curso is None:
                raise NoEncontrado(MENSAJE_CODIGO_INVALIDO)
            self._cursos.inscribir(sesion, curso["id"], estudiante_id)
            mis_cursos = self._cursos.cursos_de_estudiante(sesion, estudiante_id)
        return next(c for c in mis_cursos if c["id"] == curso["id"])

    def mis_cursos(self, estudiante_id: str) -> list[Fila]:
        with self._abrir_sesion() as sesion:
            return self._cursos.cursos_de_estudiante(sesion, estudiante_id)

    # --- Privados ---------------------------------------------------------------
    def _curso_propio(
        self, sesion: Any, usuario: CurrentUser, curso_id: int, *, bloquear: bool = False
    ) -> Fila:
        """Un curso ajeno responde 404 (no 403) para no revelar que existe.
        El administrador puede operar cualquier curso."""
        curso = self._cursos.obtener(sesion, curso_id, bloquear=bloquear)
        es_suyo = curso is not None and (
            curso["docente_id"] == usuario.id or usuario.rol == ROL_ADMIN
        )
        if not es_suyo:
            raise NoEncontrado(f"No existe el curso {curso_id}")
        return curso
