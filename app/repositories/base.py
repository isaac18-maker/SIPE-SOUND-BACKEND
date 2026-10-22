# =========================================================
# Contratos (interfaces) de acceso a datos. Los servicios dependen
# de estos protocolos, no de Supabase: en la Fase 3 se agregan
# implementaciones SQLAlchemy intercambiables (HU-B-301).
# =========================================================
from typing import Any, Protocol

Fila = dict[str, Any]


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
