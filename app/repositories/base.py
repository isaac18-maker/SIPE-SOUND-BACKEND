# =========================================================
# Contratos (interfaces) de acceso a datos. Los servicios dependen
# de estos protocolos, no de Supabase: en la Fase 3 se agregan
# implementaciones SQLAlchemy intercambiables (HU-B-301).
# =========================================================
from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import Any, Protocol

Fila = dict[str, Any]

# Abre una unidad de trabajo (sesion con commit/rollback). Hoy: session_scope().
AbrirSesion = Callable[[], AbstractContextManager[Any]]


class LectorBloques(Protocol):
    def listar(self) -> list[Fila]: ...


class LectorLecciones(Protocol):
    def listar(self) -> list[Fila]: ...
    def obtener(self, leccion_id: int) -> Fila | None: ...


class LectorEjercicios(Protocol):
    def listar(self) -> list[Fila]: ...


class LectorAcordes(Protocol):
    def listar(self) -> list[Fila]: ...


class VerificadorExistencia(Protocol):
    def existe(self, contenido_id: int) -> bool: ...


class RepositorioProgreso(Protocol):
    def listar(self, usuario_id: str, token: str) -> list[Fila]: ...
    def obtener(self, usuario_id: str, tipo: str, contenido_id: int, token: str) -> Fila | None: ...
    def guardar(self, registro: Fila, token: str) -> list[Fila]: ...


class LectorQuiz(Protocol):
    def preguntas_publicas(self, bloque_id: int) -> list[Fila]: ...
    def preguntas_con_respuesta(self, bloque_id: int) -> list[Fila]: ...


class RepositorioPerfiles(Protocol):
    """Opera dentro de la sesion que abre el servicio (unidad de trabajo)."""

    def obtener(self, sesion: Any, usuario_id: str) -> Fila | None: ...
    def obtener_para_actualizar(self, sesion: Any, usuario_id: str) -> Fila | None: ...
    def contar_por_rol(self, sesion: Any, rol: str) -> int: ...
    def actualizar_rol(self, sesion: Any, usuario_id: str, rol: str) -> Fila: ...


class RepositorioProgresoContenido(Protocol):
    """Progreso por leccion y por ejercicio. Opera dentro de la sesion del servicio."""

    def listar_lecciones(self, sesion: Any, estudiante_id: str) -> list[Fila]: ...
    def listar_ejercicios(self, sesion: Any, estudiante_id: str) -> list[Fila]: ...
    def registrar_leccion(
        self, sesion: Any, estudiante_id: str, leccion_id: int, *, porcentaje: int, completado: bool
    ) -> Fila: ...
    def registrar_ejercicio(
        self,
        sesion: Any,
        estudiante_id: str,
        ejercicio_id: int,
        *,
        porcentaje: int,
        completado: bool,
        mejor_bpm: int | None,
    ) -> Fila: ...
    def totales_catalogo(self, sesion: Any) -> dict[str, int]: ...
