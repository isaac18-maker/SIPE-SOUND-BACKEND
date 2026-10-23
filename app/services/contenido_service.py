# =========================================================
# Contenido editable desde el panel (HU-B-309). Un solo servicio para
# lecciones, ejercicios y bloques; cada uno se configura en el container.
# - Se crea en borrador. Contenido ajeno: 404 (el admin ve todo).
# - Estados: TRANSICIONES es la unica fuente de la maquina de estados.
# - Borrar algo en uso: 409 con la sugerencia de archivar.
# =========================================================
from typing import Any, Protocol

from app.core.constants import ESTADO_ARCHIVADO, ESTADO_BORRADOR, ESTADO_PUBLICADO, ROL_ADMIN
from app.core.errors import Conflicto, NoEncontrado, ReglaNegocio, ValidacionError
from app.core.security import CurrentUser
from app.repositories.base import AbrirSesion, Fila

TRANSICIONES: dict[str, set[str]] = {
    ESTADO_BORRADOR: {ESTADO_PUBLICADO},
    ESTADO_PUBLICADO: {ESTADO_ARCHIVADO},
    ESTADO_ARCHIVADO: {ESTADO_BORRADOR},
}


class RepositorioContenido(Protocol):
    def listar(
        self,
        sesion: Any,
        filtros: dict[str, Any],
        *,
        autor_id: str | None,
        pagina: int,
        por_pagina: int,
    ) -> tuple[list[Fila], int]: ...
    def obtener(self, sesion: Any, contenido_id: int, *, bloquear: bool = False) -> Fila | None: ...
    def crear(self, sesion: Any, datos: Fila) -> Fila: ...
    def actualizar(self, sesion: Any, contenido_id: int, cambios: Fila) -> Fila: ...
    def cambiar_estado(self, sesion: Any, contenido_id: int, estado: str) -> Fila: ...
    def en_uso(self, sesion: Any, contenido_id: int) -> bool: ...
    def eliminar(self, sesion: Any, contenido_id: int) -> None: ...


class RepositorioCatalogo(Protocol):
    def existe(self, sesion: Any, tabla: str, ident: int) -> bool: ...
    def acordes_faltantes(self, sesion: Any, nombres: list[str]) -> list[str]: ...


class ContenidoService:
    def __init__(
        self,
        abrir_sesion: AbrirSesion,
        repositorio: RepositorioContenido,
        catalogo: RepositorioCatalogo,
        *,
        nombre: str,
        con_autor: bool,
        referencias: dict[str, str],
        en_uso: str,
    ) -> None:
        """nombre: "la lección"; referencias: campo -> tabla (p. ej. bloque_id -> bloques);
        en_uso: mensaje del 409 al borrar."""
        self._abrir_sesion = abrir_sesion
        self._repo = repositorio
        self._catalogo = catalogo
        self._nombre = nombre
        self._con_autor = con_autor
        self._referencias = referencias
        self._mensaje_en_uso = en_uso

    def listar(
        self, usuario: CurrentUser, filtros: dict[str, Any], *, pagina: int, por_pagina: int
    ) -> tuple[list[Fila], int]:
        """El docente ve lo suyo; el admin, todo."""
        autor = None if self._ve_todo(usuario) else usuario.id
        with self._abrir_sesion() as sesion:
            return self._repo.listar(
                sesion, filtros, autor_id=autor, pagina=pagina, por_pagina=por_pagina
            )

    def obtener(self, usuario: CurrentUser, contenido_id: int) -> Fila:
        with self._abrir_sesion() as sesion:
            return self._propio(sesion, usuario, contenido_id)

    def crear(self, usuario: CurrentUser, datos: Fila) -> Fila:
        with self._abrir_sesion() as sesion:
            self._exigir_referencias(sesion, datos)
            nuevo = {**datos, "estado": ESTADO_BORRADOR}
            if self._con_autor:
                nuevo["autor_id"] = usuario.id
            return self._repo.crear(sesion, nuevo)

    def actualizar(self, usuario: CurrentUser, contenido_id: int, cambios: Fila) -> Fila:
        with self._abrir_sesion() as sesion:
            self._propio(sesion, usuario, contenido_id, bloquear=True)
            self._exigir_referencias(sesion, cambios)
            return self._repo.actualizar(sesion, contenido_id, cambios)

    def cambiar_estado(self, usuario: CurrentUser, contenido_id: int, estado: str) -> Fila:
        with self._abrir_sesion() as sesion:
            actual = self._propio(sesion, usuario, contenido_id, bloquear=True)
            if actual["estado"] == estado:
                return actual  # idempotente
            if estado not in TRANSICIONES[actual["estado"]]:
                permitidos = ", ".join(sorted(TRANSICIONES[actual["estado"]]))
                raise ReglaNegocio(
                    f"No se puede pasar de {actual['estado']} a {estado}. "
                    f"Desde {actual['estado']} solo a: {permitidos}."
                )
            return self._repo.cambiar_estado(sesion, contenido_id, estado)

    def eliminar(self, usuario: CurrentUser, contenido_id: int) -> None:
        with self._abrir_sesion() as sesion:
            self._propio(sesion, usuario, contenido_id, bloquear=True)
            if self._repo.en_uso(sesion, contenido_id):
                raise Conflicto(
                    self._mensaje_en_uso, details=[{"campo": "sugerencia", "mensaje": "archivar"}]
                )
            self._repo.eliminar(sesion, contenido_id)

    # --- Privados ---------------------------------------------------------------
    def _ve_todo(self, usuario: CurrentUser) -> bool:
        return not self._con_autor or usuario.rol == ROL_ADMIN

    def _propio(
        self, sesion: Any, usuario: CurrentUser, contenido_id: int, *, bloquear: bool = False
    ) -> Fila:
        fila = self._repo.obtener(sesion, contenido_id, bloquear=bloquear)
        if fila is None or not (self._ve_todo(usuario) or fila.get("autor_id") == usuario.id):
            raise NoEncontrado(f"No existe {self._nombre} {contenido_id}")
        return fila

    def _exigir_referencias(self, sesion: Any, datos: Fila) -> None:
        errores = [
            {"campo": campo, "mensaje": f"No existe ({tabla} {datos[campo]})."}
            for campo, tabla in self._referencias.items()
            if datos.get(campo) is not None
            and not self._catalogo.existe(sesion, tabla, datos[campo])
        ]
        if datos.get("acordes"):
            faltantes = self._catalogo.acordes_faltantes(sesion, datos["acordes"])
            if faltantes:
                errores.append(
                    {"campo": "acordes", "mensaje": f"No existen: {', '.join(faltantes)}."}
                )
        if errores:
            raise ValidacionError(details=errores)
