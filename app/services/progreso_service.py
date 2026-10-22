from app.core.constants import TIPO_LECCION
from app.core.errors import NoEncontrado
from app.repositories.base import Fila, RepositorioProgreso, VerificadorExistencia
from app.schemas.progreso import ProgresoCreate


class ProgresoService:
    def __init__(
        self,
        repositorio: RepositorioProgreso,
        lecciones: VerificadorExistencia,
        ejercicios: VerificadorExistencia,
    ) -> None:
        self._repositorio = repositorio
        self._lecciones = lecciones
        self._ejercicios = ejercicios

    def listar(self, usuario_id: str, token: str) -> list[Fila]:
        return self._repositorio.listar(usuario_id, token)

    def guardar(self, usuario_id: str, token: str, datos: ProgresoCreate) -> list[Fila]:
        """Solo se registra progreso sobre contenido que existe."""
        verificador = self._lecciones if datos.tipo == TIPO_LECCION else self._ejercicios
        if not verificador.existe(datos.contenido_id):
            raise NoEncontrado(f"No existe {datos.tipo} con id {datos.contenido_id}")

        registro = {"usuario_id": usuario_id, **datos.model_dump()}
        return self._repositorio.guardar(registro, token)
