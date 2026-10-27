# =========================================================
# Administracion de cuentas (HU-B-405): ver quien no verifico su correo, reenviarle el codigo,
# verificar a mano, suspender, reactivar y eliminar. Toda accion queda en acciones_admin sin
# datos sensibles (nunca contrasenas ni codigos; de una cuenta eliminada solo el correo
# enmascarado). Un administrador no puede suspender ni eliminar a otro ni a si mismo.
# =========================================================
import logging
from collections.abc import Callable
from typing import Any

from app.core.constants import (
    CORREO_CUENTA_SUSPENDIDA,
    CORREO_ROL_CAMBIADO,
    CORREO_VERIFICAR,
    CUENTA_ACTIVA,
    CUENTA_PENDIENTE,
    CUENTA_SUSPENDIDA,
    PROPOSITO_VERIFICAR_CORREO,
    ROL_ADMIN,
    ROL_DOCENTE,
    ROL_ESTUDIANTE,
    VIGENCIA_CODIGO_MIN,
)
from app.core.errors import (
    Conflicto,
    DemasiadasSolicitudes,
    NoEncontrado,
    ReglaNegocio,
    SinPermiso,
)
from app.core.privacidad import enmascarar_email
from app.repositories.base import (
    AbrirSesion,
    RepositorioAcciones,
    RepositorioAdminCuentas,
    RepositorioCuentas,
)
from app.services.codigo_service import CodigoService
from app.services.verificacion_service import EnviadorDeCorreo, enlace_de_verificacion

logger = logging.getLogger(__name__)

ACCIONES_RECIENTES = 20
MENSAJE_YA_VERIFICADA = "Esa cuenta ya tiene el correo verificado."
MENSAJE_ESPERA = "Espera un minuto antes de reenviar el código."
MENSAJE_PROTEGIDA = "No puedes suspender ni eliminar a un administrador ni a tu propia cuenta."
MENSAJE_CONFIRMACION = "El correo de confirmación no coincide con el de la cuenta."
MENSAJE_CORREO_PROPIO = "Para cambiar tu correo usa Mi cuenta: ahí se confirma con tu contraseña."
MENSAJE_CORREO_EN_USO = "Ese correo ya está en uso por otra cuenta."
MENSAJE_ROL_PROPIO = "No puedes cambiar tu propio rol."
MOTIVO_POR_DEFECTO = "Suspendida por un administrador."
MOTIVO_VERIFICACION = "Verificada por un administrador."
ETIQUETA_ROL = {ROL_ESTUDIANTE: "Estudiante", ROL_DOCENTE: "Docente", ROL_ADMIN: "Administrador"}


class AdminCuentasService:
    def __init__(  # noqa: PLR0913, PLR0917 - dependencias inyectadas desde app/container.py
        self,
        abrir_sesion: AbrirSesion,
        cuentas_admin: RepositorioAdminCuentas,
        cuentas: RepositorioCuentas,
        codigos: CodigoService,
        correo: EnviadorDeCorreo,
        auditoria: RepositorioAcciones,
        progreso_de: Callable[[str], dict[str, Any]],
        cambiar_rol: Callable[[str, str, str], dict[str, Any]],
        *,
        origen_frontend: str,
    ) -> None:
        self._abrir_sesion = abrir_sesion
        self._cuentas_admin = cuentas_admin
        self._cuentas = cuentas
        self._codigos = codigos
        self._correo = correo
        self._auditoria = auditoria
        self._progreso_de = progreso_de
        self._cambiar_rol = cambiar_rol
        self._origen_frontend = origen_frontend

    # --- Consulta -------------------------------------------------------------------------
    def listar(
        self, filtros: dict[str, Any]
    ) -> tuple[list[dict], int, dict[str, int], dict[str, int]]:
        """Devuelve (filas, total, totales por estado, totales por rol). Los totales no
        dependen de los filtros."""
        with self._abrir_sesion() as sesion:
            filas, total = self._cuentas_admin.listar(sesion, **filtros)
            contados = self._cuentas_admin.totales_por_estado(sesion)
            por_rol = self._cuentas_admin.totales_por_rol(sesion)
        totales = {
            e: contados.get(e, 0) for e in (CUENTA_PENDIENTE, CUENTA_ACTIVA, CUENTA_SUSPENDIDA)
        }
        roles = {r: por_rol.get(r, 0) for r in (ROL_ESTUDIANTE, ROL_DOCENTE, ROL_ADMIN)}
        return filas, total, totales, roles

    def detalle(self, usuario_id: str) -> dict[str, Any]:
        with self._abrir_sesion() as sesion:
            cuenta = self._obtener(sesion, usuario_id)
            cuenta["inscripciones"] = self._cuentas_admin.inscripciones(sesion, usuario_id)
            cuenta["cursos_a_cargo"] = self._cuentas_admin.cursos_a_cargo(sesion, usuario_id)
            cuenta["acciones"] = self._auditoria.ultimas(sesion, usuario_id, ACCIONES_RECIENTES)
        # El progreso lo calcula su propio servicio (abre su propia sesion).
        cuenta["progreso"] = (
            self._progreso_de(usuario_id) if cuenta["rol"] == ROL_ESTUDIANTE else None
        )
        return cuenta

    # --- Verificacion del correo ----------------------------------------------------------
    def reenviar_verificacion(self, admin_id: str, usuario_id: str) -> str:
        """Devuelve el correo al que se envio el codigo."""
        with self._abrir_sesion() as sesion:
            cuenta = self._obtener(sesion, usuario_id)
            if cuenta["correo_verificado_en"] is not None:
                raise Conflicto(MENSAJE_YA_VERIFICADA)
            if self._codigos.hay_espera(sesion, usuario_id, PROPOSITO_VERIFICAR_CORREO):
                raise DemasiadasSolicitudes(MENSAJE_ESPERA)
            codigo = self._codigos.emitir(
                sesion, usuario_id, PROPOSITO_VERIFICAR_CORREO, cuenta["email"]
            )
            self._auditoria.registrar(
                sesion,
                admin_id=admin_id,
                usuario_id=usuario_id,
                accion="reenviar_verificacion",
            )
        # Despues de confirmar: el correo no puede llegar antes de que el codigo exista.
        self._enviar_codigo(cuenta, codigo)
        return cuenta["email"]

    def verificar_manual(self, admin_id: str, usuario_id: str, motivo: str | None) -> None:
        """Para aulas donde la persona no puede abrir su correo. Es la unica forma de verificar
        sin el codigo, por eso exige un motivo y deja rastro."""
        with self._abrir_sesion() as sesion:
            cuenta = self._obtener(sesion, usuario_id)
            if cuenta["correo_verificado_en"] is not None:
                raise Conflicto(MENSAJE_YA_VERIFICADA)
            # El trigger de la base aplica aqui el rol docente si el correo esta preautorizado.
            self._cuentas.marcar_verificada(sesion, usuario_id)
            self._cuentas.confirmar_en_proveedor(sesion, usuario_id)
            self._codigos.invalidar(sesion, usuario_id, PROPOSITO_VERIFICAR_CORREO)
            self._auditoria.registrar(
                sesion,
                admin_id=admin_id,
                usuario_id=usuario_id,
                accion="verificar_manual",
                detalle={"motivo": motivo or MOTIVO_VERIFICACION},
            )

    # --- Suspension -----------------------------------------------------------------------
    def cambiar_estado(
        self,
        admin_id: str,
        usuario_id: str,
        estado: str,
        motivo: str | None,
        *,
        notificar: bool = False,
    ) -> dict[str, str]:
        with self._abrir_sesion() as sesion:
            cuenta = self._obtener(sesion, usuario_id)
            if estado == CUENTA_SUSPENDIDA:
                self._exigir_gestionable(admin_id, cuenta)
                motivo = motivo or MOTIVO_POR_DEFECTO
                self._cuentas_admin.suspender(sesion, usuario_id, motivo)
                # Sin sesiones abiertas: el access token vence en minutos, el refresh no sirve.
                self._cuentas.cerrar_sesiones(sesion, usuario_id)
                accion, detalle = "suspender", {"motivo": motivo}
            else:
                self._cuentas_admin.reactivar(sesion, usuario_id)
                accion, detalle = "reactivar", {}
            self._auditoria.registrar(
                sesion, admin_id=admin_id, usuario_id=usuario_id, accion=accion, detalle=detalle
            )
            nuevo = self._obtener(sesion, usuario_id)["estado"]
        if notificar and estado == CUENTA_SUSPENDIDA:
            self._correo.enviar(
                CORREO_CUENTA_SUSPENDIDA,
                cuenta["email"],
                {"nombre": cuenta["nombre"]},
                usuario_id=usuario_id,
            )
        return {"id": usuario_id, "estado": nuevo}

    # --- Edicion de datos -----------------------------------------------------------------
    def editar(
        self, admin_id: str, usuario_id: str, nombre: str, apellido: str, email: str
    ) -> dict[str, Any]:
        """Nombre, apellido y correo. Un correo nuevo deja la cuenta pendiente y envía un
        código para verificarlo; el administrador no cambia su propio correo aquí."""
        codigo: str | None = None
        with self._abrir_sesion() as sesion:
            cuenta = self._obtener(sesion, usuario_id)
            cambia_correo = email != cuenta["email"].lower()
            if cambia_correo:
                if usuario_id == admin_id:
                    raise SinPermiso(MENSAJE_CORREO_PROPIO)
                if self._cuentas.correo_en_uso(sesion, email, excepto_id=usuario_id):
                    raise Conflicto(MENSAJE_CORREO_EN_USO)
            self._cuentas_admin.actualizar_nombre(sesion, usuario_id, nombre, apellido)
            if cambia_correo:
                self._cuentas.cambiar_correo(sesion, usuario_id, email)
                self._cuentas_admin.quitar_verificacion(sesion, usuario_id)
                self._codigos.invalidar(sesion, usuario_id, PROPOSITO_VERIFICAR_CORREO)
                codigo = self._codigos.emitir(sesion, usuario_id, PROPOSITO_VERIFICAR_CORREO, email)
            self._auditoria.registrar(
                sesion,
                admin_id=admin_id,
                usuario_id=usuario_id,
                accion="editar_cuenta",
                detalle={"correo": cambia_correo},
            )
            editada = self._obtener(sesion, usuario_id)
        if codigo is not None:
            self._enviar_codigo(editada, codigo)
        return editada

    # --- Avisos y acciones en lote --------------------------------------------------------
    def avisar_cambio_de_rol(self, usuario_id: str, rol: str) -> None:
        with self._abrir_sesion() as sesion:
            cuenta = self._obtener(sesion, usuario_id)
        self._correo.enviar(
            CORREO_ROL_CAMBIADO,
            cuenta["email"],
            {"nombre": cuenta["nombre"], "rol": ETIQUETA_ROL[rol].lower()},
            usuario_id=usuario_id,
        )

    def en_lote(
        self,
        admin_id: str,
        ids: list[str],
        accion: str,
        *,
        rol: str | None,
        notificar: bool,
    ) -> dict[str, Any]:
        """Aplica una acción a cada cuenta válida. Omite la propia cuenta y las que ya están
        en ese estado, y devuelve cuáles cambiaron y cuáles se omitieron (con su motivo)."""
        cambiadas: list[str] = []
        omitidas: list[dict[str, str]] = []
        for usuario_id in ids:
            try:
                self._aplicar(admin_id, usuario_id, accion, rol, notificar)
                cambiadas.append(usuario_id)
            except (Conflicto, DemasiadasSolicitudes, NoEncontrado, ReglaNegocio, SinPermiso) as e:
                omitidas.append({"id": usuario_id, "motivo": str(e)})
        return {"cambiadas": cambiadas, "omitidas": omitidas}

    def _aplicar(
        self, admin_id: str, usuario_id: str, accion: str, rol: str | None, notificar: bool
    ) -> None:
        if accion == "reenviar":
            self.reenviar_verificacion(admin_id, usuario_id)
            return
        with self._abrir_sesion() as sesion:
            cuenta = self._obtener(sesion, usuario_id)
        if accion == "rol":
            if usuario_id == admin_id:
                raise SinPermiso(MENSAJE_ROL_PROPIO)
            if cuenta["rol"] == rol:
                raise ReglaNegocio("Ya tiene ese rol.")
            self._cambiar_rol(admin_id, usuario_id, rol)
            if notificar:
                self.avisar_cambio_de_rol(usuario_id, rol)
        elif accion == "suspender":
            if cuenta["estado"] == CUENTA_SUSPENDIDA:
                raise ReglaNegocio("Ya está suspendida.")
            self.cambiar_estado(admin_id, usuario_id, CUENTA_SUSPENDIDA, None, notificar=notificar)
        else:
            if cuenta["estado"] != CUENTA_SUSPENDIDA:
                raise ReglaNegocio("Ya está activa.")
            self.cambiar_estado(admin_id, usuario_id, CUENTA_ACTIVA, None)

    # --- Eliminacion ----------------------------------------------------------------------
    def eliminar(self, admin_id: str, usuario_id: str, confirmacion: str) -> None:
        """Borrado fisico (derecho de supresion): no se puede deshacer, por eso exige escribir
        el correo de la cuenta."""
        with self._abrir_sesion() as sesion:
            cuenta = self._obtener(sesion, usuario_id)
            self._exigir_gestionable(admin_id, cuenta)
            if cuenta["rol"] == ROL_DOCENTE:
                a_cargo = self._cuentas_admin.contar_cursos_a_cargo(sesion, usuario_id)
                if a_cargo:
                    raise Conflicto(
                        f"Reasigna sus cursos a cargo ({a_cargo}) antes de eliminar la cuenta."
                    )
            if confirmacion != cuenta["email"].lower():
                raise ReglaNegocio(MENSAJE_CONFIRMACION)
            # La auditoria se escribe ANTES de borrar y no guarda el correo completo.
            self._auditoria.registrar(
                sesion,
                admin_id=admin_id,
                usuario_id=usuario_id,
                accion="eliminar",
                detalle={"correo": enmascarar_email(cuenta["email"]), "rol": cuenta["rol"]},
            )
            self._cuentas.eliminar_cuenta(sesion, usuario_id)
        logger.info("Cuenta eliminada: admin=%s usuario=%s", admin_id, usuario_id)

    # --- Auxiliares -----------------------------------------------------------------------
    def _enviar_codigo(self, cuenta: dict[str, Any], codigo: str) -> None:
        self._correo.enviar(
            CORREO_VERIFICAR,
            cuenta["email"],
            {
                "nombre": cuenta["nombre"],
                "codigo": codigo,
                "minutos": VIGENCIA_CODIGO_MIN[PROPOSITO_VERIFICAR_CORREO],
                "enlace": enlace_de_verificacion(self._origen_frontend, cuenta["email"]),
            },
            usuario_id=cuenta["id"],
        )

    def _obtener(self, sesion: Any, usuario_id: str) -> dict[str, Any]:
        cuenta = self._cuentas_admin.obtener(sesion, usuario_id)
        if cuenta is None:
            raise NoEncontrado(f"No existe el usuario {usuario_id}")
        return cuenta

    @staticmethod
    def _exigir_gestionable(admin_id: str, cuenta: dict[str, Any]) -> None:
        if cuenta["rol"] == ROL_ADMIN or cuenta["id"] == admin_id:
            raise SinPermiso(MENSAJE_PROTEGIDA)
