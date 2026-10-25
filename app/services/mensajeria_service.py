# =========================================================
# Mensajeria interna (HU-B-409). Las reglas de "quien le puede escribir a quien" viven SOLO
# aqui (_puede_escribir_a y _validar_destino) y se aplican igual al enviar, al responder, al
# calcular `puede_responder` y al sugerir destinatarios:
#   - admin: a cualquiera, y a todos los estudiantes, docentes, administradores o todos;
#   - docente: a un estudiante de un curso activo suyo, a cualquier docente o admin, a un
#     curso suyo, a todos sus estudiantes, a todos los docentes y a los admins;
#   - estudiante: SOLO a los docentes de los cursos activos donde esta inscrito.
# Es interna: no envia correos. Nunca devuelve correos. Los avisos de grupo solo llegan a
# cuentas con el correo verificado y no suspendidas.
# =========================================================
from typing import Any, Protocol

from app.core.constants import (
    ALCANCE_CURSO,
    ALCANCE_ESTUDIANTES_DOCENTE,
    ALCANCE_ROL_ADMIN,
    ALCANCE_ROL_DOCENTE,
    ALCANCE_ROL_ESTUDIANTE,
    ALCANCE_TODOS,
    ALCANCE_USUARIO,
    ALCANCES_POR_ROL,
    AVISOS_DE_GRUPO_POR_HORA,
    DESTINATARIOS_SUGERIDOS_MAX,
    EXTRACTO_MENSAJE_MAX,
    MENSAJES_POR_HORA,
    ROL_ADMIN,
    ROL_DOCENTE,
    ROL_ESTUDIANTE,
)
from app.core.errors import DemasiadasSolicitudes, NoEncontrado, ReglaNegocio, SinPermiso
from app.core.security import CurrentUser
from app.repositories.base import AbrirSesion, Fila

MENSAJE_DESTINO = "No puedes enviar mensajes a ese destino."
MENSAJE_ESTUDIANTE = "Solo puedes escribirle a los docentes de tus cursos."
MENSAJE_GRUPO_VACIO = (
    "No hay a quién enviarle este mensaje. "
    "Las cuentas sin verificar o suspendidas no reciben mensajes."
)
MENSAJE_LIMITE = "Enviaste muchos mensajes seguidos. Espera un rato antes de escribir otro."
MENSAJE_SIN_ORIGINAL = "No encontramos el mensaje que quieres responder."
MENSAJE_ORIGEN_ELIMINADO = "No puedes responder: la persona que lo envió ya no tiene cuenta."
MENSAJE_HILO = "No encontramos esa conversación."

ETIQUETAS_GRUPO = {
    ALCANCE_ESTUDIANTES_DOCENTE: "Todos mis estudiantes",
    ALCANCE_ROL_ESTUDIANTE: "Todos los estudiantes",
    ALCANCE_ROL_DOCENTE: "Todos los docentes",
    ALCANCE_ROL_ADMIN: "Los administradores",
    ALCANCE_TODOS: "Todas las cuentas activas",
}
ETIQUETA_ROL = {ROL_ESTUDIANTE: "Estudiante", ROL_DOCENTE: "Docente", ROL_ADMIN: "Administrador"}


class RepositorioMensajeria(Protocol):
    def perfil_basico(self, sesion: Any, usuario_id: str) -> Fila | None: ...
    def comparten_curso_activo(self, sesion: Any, docente_id: str, estudiante_id: str) -> bool: ...
    def curso_activo_de_docente(self, sesion: Any, curso_id: int, docente_id: str) -> bool: ...
    def mensaje_recibido(self, sesion: Any, mensaje_id: str, usuario_id: str) -> Fila | None: ...
    def contar_enviados_ultima_hora(self, sesion: Any, usuario_id: str) -> tuple[int, int]: ...
    def crear(self, sesion: Any, **datos: Any) -> Fila: ...
    def agregar_destinatarios(self, sesion: Any, mensaje_id: str, **datos: Any) -> int: ...
    def agregar_remitente(self, sesion: Any, mensaje_id: str, remitente_id: str) -> None: ...
    def bandeja(self, sesion: Any, usuario_id: str, **filtros: Any) -> tuple[list[Fila], int]: ...
    def hilo(self, sesion: Any, usuario_id: str, hilo_id: str) -> list[Fila]: ...
    def marcar_hilo_leido(self, sesion: Any, usuario_id: str, hilo_id: str) -> None: ...
    def archivar_hilo(
        self, sesion: Any, usuario_id: str, hilo_id: str, *, archivado: bool
    ) -> int: ...
    def marcar_ultimo_recibido_no_leido(
        self, sesion: Any, usuario_id: str, hilo_id: str
    ) -> bool: ...
    def contar_no_leidos(self, sesion: Any, usuario_id: str) -> int: ...
    def docentes_de_estudiante(
        self, sesion: Any, usuario_id: str, q: str | None, limite: int
    ) -> list[Fila]: ...
    def cursos_de_docente(
        self, sesion: Any, usuario_id: str, q: str | None, limite: int
    ) -> list[Fila]: ...
    def estudiantes_de_docente(
        self, sesion: Any, usuario_id: str, q: str, limite: int
    ) -> list[Fila]: ...
    def personas(
        self, sesion: Any, usuario_id: str, roles: list[str], q: str, limite: int
    ) -> list[Fila]: ...


def _nombre(fila: Fila, prefijo: str = "") -> str:
    partes = [fila.get(f"{prefijo}nombre"), fila.get(f"{prefijo}apellido")]
    return " ".join(p for p in partes if p)


def _remitente(fila: Fila, prefijo: str) -> Fila | None:
    """Quien envio el mensaje; None si su cuenta ya no existe. Nunca lleva correo."""
    rol = fila.get(f"{prefijo}rol")
    if rol is None:
        return None
    return {
        "nombre": fila[f"{prefijo}nombre"],
        "apellido": fila[f"{prefijo}apellido"],
        "rol": rol,
    }


class MensajeriaService:
    def __init__(self, abrir_sesion: AbrirSesion, mensajes: RepositorioMensajeria) -> None:
        self._abrir_sesion = abrir_sesion
        self._mensajes = mensajes

    # --- Reglas de destino (UN solo lugar) -------------------------------------------------
    def _puede_escribir_a(self, sesion: Any, usuario: CurrentUser, destino_id: str) -> bool:
        destino = self._mensajes.perfil_basico(sesion, destino_id)
        if destino is None or destino_id == usuario.id:
            return False
        if usuario.rol == ROL_ADMIN:
            return True
        if usuario.rol == ROL_DOCENTE:
            if destino["rol"] in {ROL_DOCENTE, ROL_ADMIN}:
                return True
            return destino["rol"] == ROL_ESTUDIANTE and self._mensajes.comparten_curso_activo(
                sesion, usuario.id, destino_id
            )
        # Estudiante: solo a los docentes de sus cursos activos.
        return destino["rol"] == ROL_DOCENTE and self._mensajes.comparten_curso_activo(
            sesion, destino_id, usuario.id
        )

    def _validar_destino(
        self,
        sesion: Any,
        usuario: CurrentUser,
        alcance: str,
        destinatario_id: str | None,
        curso_id: int | None,
    ) -> None:
        negado = MENSAJE_ESTUDIANTE if usuario.rol == ROL_ESTUDIANTE else MENSAJE_DESTINO
        if alcance not in ALCANCES_POR_ROL.get(usuario.rol, frozenset()):
            raise SinPermiso(negado)
        if alcance == ALCANCE_USUARIO and not self._puede_escribir_a(
            sesion, usuario, destinatario_id or ""
        ):
            raise SinPermiso(negado)
        if alcance == ALCANCE_CURSO and not self._mensajes.curso_activo_de_docente(
            sesion, curso_id or 0, usuario.id
        ):
            raise SinPermiso(negado)

    def _exigir_dentro_del_limite(self, sesion: Any, usuario: CurrentUser, alcance: str) -> None:
        total, avisos = self._mensajes.contar_enviados_ultima_hora(sesion, usuario.id)
        if total >= MENSAJES_POR_HORA.get(usuario.rol, 0):
            raise DemasiadasSolicitudes(MENSAJE_LIMITE)
        if alcance != ALCANCE_USUARIO and avisos >= AVISOS_DE_GRUPO_POR_HORA:
            raise DemasiadasSolicitudes(MENSAJE_LIMITE)

    # --- Enviar ---------------------------------------------------------------------------
    def enviar(self, usuario: CurrentUser, datos: dict[str, Any]) -> dict[str, Any]:
        with self._abrir_sesion() as sesion:
            hilo_id = None
            respuesta_a_id = datos.get("respuesta_a_id")
            if respuesta_a_id:
                original = self._mensajes.mensaje_recibido(sesion, respuesta_a_id, usuario.id)
                if original is None:
                    raise NoEncontrado(MENSAJE_SIN_ORIGINAL)
                if original["remitente_id"] is None:
                    raise ReglaNegocio(MENSAJE_ORIGEN_ELIMINADO)
                # Una respuesta va SOLO a quien escribio, en su mismo hilo y con su asunto.
                alcance, destinatario_id, curso_id = ALCANCE_USUARIO, original["remitente_id"], None
                asunto, hilo_id = original["asunto"], original["hilo_id"]
            else:
                alcance = datos["alcance"]
                destinatario_id, curso_id = datos.get("destinatario_id"), datos.get("curso_id")
                asunto = datos["asunto"]
            self._exigir_dentro_del_limite(sesion, usuario, alcance)
            self._validar_destino(sesion, usuario, alcance, destinatario_id, curso_id)
            mensaje = self._mensajes.crear(
                sesion,
                remitente_id=usuario.id,
                asunto=asunto,
                cuerpo=datos["cuerpo"],
                alcance=alcance,
                curso_id=curso_id if alcance == ALCANCE_CURSO else None,
                respuesta_a_id=respuesta_a_id,
                hilo_id=hilo_id,
            )
            destinatarios = self._mensajes.agregar_destinatarios(
                sesion,
                mensaje["id"],
                alcance=alcance,
                remitente_id=usuario.id,
                destinatario_id=destinatario_id,
                curso_id=curso_id,
            )
            if destinatarios == 0:
                # Dentro del with: la transaccion se deshace y no queda un mensaje sin nadie.
                raise ReglaNegocio(MENSAJE_GRUPO_VACIO)
            self._mensajes.agregar_remitente(sesion, mensaje["id"], usuario.id)
        return {"id": mensaje["id"], "hilo_id": mensaje["hilo_id"], "destinatarios": destinatarios}

    # --- Bandeja e hilos ------------------------------------------------------------------
    def bandeja(self, usuario: CurrentUser, filtros: dict[str, Any]) -> tuple[list[Fila], int]:
        with self._abrir_sesion() as sesion:
            filas, total = self._mensajes.bandeja(
                sesion, usuario.id, extracto=EXTRACTO_MENSAJE_MAX, **filtros
            )
        return [self._hilo_de_bandeja(f) for f in filas], total

    @staticmethod
    def _hilo_de_bandeja(fila: Fila) -> Fila:
        return {
            "hilo_id": fila["hilo_id"],
            "asunto": fila["asunto"],
            "alcance": fila["alcance"],
            "curso": fila["curso"],
            "no_leidos": fila["no_leidos"],
            "archivado": fila["archivado"],
            "ultimo": {
                "remitente": _remitente(fila, "ultimo_"),
                "propio": fila["ultimo_propio"],
                "extracto": fila["ultimo_extracto"],
                "creado_en": fila["ultimo_creado_en"],
            },
        }

    def hilo(self, usuario: CurrentUser, hilo_id: str) -> dict[str, Any]:
        """Los mensajes del hilo que la persona envio o recibio. Los marca como leidos; cada
        uno trae `nuevo` (si no lo habia leido antes de abrirlo)."""
        with self._abrir_sesion() as sesion:
            filas = self._mensajes.hilo(sesion, usuario.id, hilo_id)
            if not filas:
                raise NoEncontrado(MENSAJE_HILO)
            self._mensajes.marcar_hilo_leido(sesion, usuario.id, hilo_id)
            ultimo_recibido = next(
                (f for f in reversed(filas) if f["remitente_id"] not in {None, usuario.id}), None
            )
            puede_responder = ultimo_recibido is not None and self._puede_escribir_a(
                sesion, usuario, ultimo_recibido["remitente_id"]
            )
        return {
            "hilo_id": hilo_id,
            "asunto": filas[0]["asunto"],
            "puede_responder": puede_responder,
            "responder_a": ultimo_recibido["id"] if puede_responder else None,
            "mensajes": [
                {
                    "id": f["id"],
                    "propio": f["remitente_id"] == usuario.id,
                    "remitente": _remitente(f, "remitente_"),
                    "cuerpo": f["cuerpo"],
                    "alcance": f["alcance"],
                    "curso": f["curso"],
                    "creado_en": f["creado_en"],
                    "nuevo": f["leido_en"] is None,
                }
                for f in filas
            ],
        }

    def editar_hilo(
        self, usuario: CurrentUser, hilo_id: str, *, archivado: bool | None, leido: bool | None
    ) -> dict[str, Any]:
        with self._abrir_sesion() as sesion:
            if not self._mensajes.hilo(sesion, usuario.id, hilo_id):
                raise NoEncontrado(MENSAJE_HILO)
            if archivado is not None:
                self._mensajes.archivar_hilo(sesion, usuario.id, hilo_id, archivado=archivado)
            if leido is True:
                self._mensajes.marcar_hilo_leido(sesion, usuario.id, hilo_id)
            elif leido is False:
                self._mensajes.marcar_ultimo_recibido_no_leido(sesion, usuario.id, hilo_id)
        return {"hilo_id": hilo_id, "archivado": archivado, "leido": leido}

    def no_leidos(self, usuario: CurrentUser) -> dict[str, int]:
        with self._abrir_sesion() as sesion:
            return {"total": self._mensajes.contar_no_leidos(sesion, usuario.id)}

    # --- A quien puedo escribirle ---------------------------------------------------------
    def destinatarios(self, usuario: CurrentUser, q: str | None) -> list[Fila]:
        """Personas, cursos y grupos a los que ESTA persona puede escribir (max. 20)."""
        limite = DESTINATARIOS_SUGERIDOS_MAX
        with self._abrir_sesion() as sesion:
            if usuario.rol == ROL_ESTUDIANTE:
                docentes = self._mensajes.docentes_de_estudiante(sesion, usuario.id, q, limite)
                return [self._persona(f, f["detalle"]) for f in docentes]
            items = self._grupos(usuario, q)
            if usuario.rol == ROL_DOCENTE:
                items += self._cursos(sesion, usuario, q, limite)
            if q:  # Sin busqueda no se vuelca la lista de personas.
                items += self._personas(sesion, usuario, q, limite)
        return items[:limite]

    @staticmethod
    def _persona(fila: Fila, detalle: str | None) -> Fila:
        return {"tipo": "usuario", "id": fila["id"], "etiqueta": _nombre(fila), "detalle": detalle}

    @staticmethod
    def _grupos(usuario: CurrentUser, q: str | None) -> list[Fila]:
        permitidos = ALCANCES_POR_ROL[usuario.rol] & ETIQUETAS_GRUPO.keys()
        grupos = [
            {"tipo": "grupo", "id": a, "etiqueta": ETIQUETAS_GRUPO[a], "detalle": None}
            for a in ETIQUETAS_GRUPO
            if a in permitidos
        ]
        if not q:
            return grupos
        return [g for g in grupos if q.casefold() in g["etiqueta"].casefold()]

    def _cursos(self, sesion: Any, usuario: CurrentUser, q: str | None, limite: int) -> list[Fila]:
        cursos = self._mensajes.cursos_de_docente(sesion, usuario.id, q, limite)
        return [
            {
                "tipo": "curso",
                "id": c["id"],
                "etiqueta": c["nombre"],
                "detalle": f"{c['estudiantes']} estudiantes",
            }
            for c in cursos
        ]

    def _personas(self, sesion: Any, usuario: CurrentUser, q: str, limite: int) -> list[Fila]:
        if usuario.rol == ROL_ADMIN:
            filas = self._mensajes.personas(
                sesion, usuario.id, [ROL_ESTUDIANTE, ROL_DOCENTE, ROL_ADMIN], q, limite
            )
            return [self._persona(f, ETIQUETA_ROL[f["rol"]]) for f in filas]
        estudiantes = self._mensajes.estudiantes_de_docente(sesion, usuario.id, q, limite)
        colegas = self._mensajes.personas(sesion, usuario.id, [ROL_DOCENTE, ROL_ADMIN], q, limite)
        return [self._persona(f, f["detalle"]) for f in estudiantes] + [
            self._persona(f, ETIQUETA_ROL[f["rol"]]) for f in colegas
        ]
