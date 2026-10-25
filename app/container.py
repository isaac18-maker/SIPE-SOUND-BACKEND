# =========================================================
# Composition root: el UNICO lugar que decide que implementacion
# de repositorio recibe cada servicio (inversion de dependencias).
# Vive fuera de core/ porque depende de services y repositories.
# Todo el acceso a datos es por SQL con una sola conexion (HU-B-315).
# =========================================================
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache

from flask import g, has_app_context
from sqlalchemy import exists

from app.core.config import get_settings
from app.core.security import CurrentUser
from app.infrastructure.correo_smtp import EnviadorArchivo, EnviadorSmtp
from app.infrastructure.database import session_scope
from app.infrastructure.supabase_auth import ClienteSupabaseAuth
from app.models.bloque import Bloque
from app.models.ejercicio import Ejercicio
from app.models.evaluacion import Evaluacion
from app.models.leccion import Leccion
from app.models.progreso_contenido import ProgresoEjercicio, ProgresoLeccion
from app.repositories.sqlalchemy.accion_admin_repository import SqlAccionAdminRepository
from app.repositories.sqlalchemy.acorde_repository import SqlAcordeRepository
from app.repositories.sqlalchemy.admin_cuentas_repository import SqlAdminCuentasRepository
from app.repositories.sqlalchemy.admin_docentes_repository import SqlAdminDocentesRepository
from app.repositories.sqlalchemy.bloque_repository import SqlBloqueRepository
from app.repositories.sqlalchemy.codigo_repository import SqlCodigoRepository
from app.repositories.sqlalchemy.contenido_repository import (
    SqlCatalogoRepository,
    SqlContenidoRepository,
)
from app.repositories.sqlalchemy.cuenta_repository import SqlCuentaRepository
from app.repositories.sqlalchemy.curso_repository import SqlCursoRepository
from app.repositories.sqlalchemy.docente_repository import SqlDocenteRepository
from app.repositories.sqlalchemy.ejercicio_repository import SqlEjercicioRepository
from app.repositories.sqlalchemy.envio_correo_repository import SqlEnvioCorreoRepository
from app.repositories.sqlalchemy.evaluacion_repository import SqlEvaluacionRepository
from app.repositories.sqlalchemy.gestion_evaluacion_repository import (
    SqlGestionEvaluacionRepository,
)
from app.repositories.sqlalchemy.leccion_repository import SqlLeccionRepository
from app.repositories.sqlalchemy.mensajeria_repository import SqlMensajeriaRepository
from app.repositories.sqlalchemy.perfil_repository import SqlPerfilRepository
from app.repositories.sqlalchemy.progreso_docente_repository import SqlProgresoDocenteRepository
from app.repositories.sqlalchemy.progreso_repository import SqlProgresoRepository
from app.repositories.sqlalchemy.ruta_repository import SqlRutaRepository
from app.repositories.sqlalchemy.seguimiento_repository import SqlSeguimientoRepository
from app.repositories.sqlalchemy.terminos_repository import SqlTerminosRepository
from app.services.acorde_service import AcordeService
from app.services.admin_cuentas_service import AdminCuentasService
from app.services.admin_cursos_service import AdminCursosService
from app.services.auth_service import AuthService
from app.services.bloque_service import BloqueService
from app.services.codigo_service import CodigoService
from app.services.contenido_service import ContenidoService
from app.services.correo_service import MARCA, CorreoService, Enviador
from app.services.cuenta_service import CuentaService
from app.services.curso_service import CursoService
from app.services.docente_service import DocenteService
from app.services.ejercicio_service import EjercicioService
from app.services.evaluacion_service import EvaluacionService
from app.services.gestion_evaluacion_service import GestionEvaluacionService
from app.services.leccion_service import LeccionService
from app.services.mensajeria_service import MensajeriaService
from app.services.perfil_service import AdminUsuariosService, PerfilService, estado_de_cuenta
from app.services.progreso_docente_service import ProgresoDocenteService
from app.services.progreso_service import ProgresoService
from app.services.recuperacion_service import RecuperacionService
from app.services.ruta_service import RutaService
from app.services.terminos_service import TerminosService, terminos_pendientes
from app.services.verificacion_service import VerificacionService


@lru_cache
def bloque_service() -> BloqueService:
    return BloqueService(SqlBloqueRepository(session_scope))


@lru_cache
def leccion_service() -> LeccionService:
    return LeccionService(SqlLeccionRepository(session_scope))


@lru_cache
def ejercicio_service() -> EjercicioService:
    return EjercicioService(SqlEjercicioRepository(session_scope))


@lru_cache
def acorde_service() -> AcordeService:
    return AcordeService(SqlAcordeRepository(session_scope))


@lru_cache
def progreso_service() -> ProgresoService:
    return ProgresoService(
        session_scope,
        SqlProgresoRepository(),
        evaluaciones=SqlEvaluacionRepository(),
        lecciones=SqlLeccionRepository(session_scope),
        ejercicios=SqlEjercicioRepository(session_scope),
    )


@lru_cache
def ruta_service() -> RutaService:
    return RutaService(session_scope, SqlRutaRepository(), SqlCursoRepository())


@lru_cache
def evaluacion_service() -> EvaluacionService:
    return EvaluacionService(
        session_scope, SqlEvaluacionRepository(), SqlCursoRepository(), ruta_service()
    )


@lru_cache
def perfil_service() -> PerfilService:
    return PerfilService(session_scope, SqlPerfilRepository())


@lru_cache
def admin_usuarios_service() -> AdminUsuariosService:
    return AdminUsuariosService(session_scope, SqlPerfilRepository(), SqlAccionAdminRepository())


@lru_cache
def curso_service() -> CursoService:
    return CursoService(
        session_scope, SqlCursoRepository(), SqlSeguimientoRepository(), ruta_service()
    )


@lru_cache
def docente_service() -> DocenteService:
    return DocenteService(session_scope, SqlDocenteRepository())


def _perfil_en_peticion(usuario_id: str) -> dict | None:
    """El perfil se lee una vez por peticion: auth_required (estado) y roles_required (rol)
    consultan a la misma persona y comparten la lectura."""
    if not has_app_context():
        return perfil_service().perfil_de(usuario_id)
    perfiles = g.setdefault("perfiles_en_peticion", {})
    if usuario_id not in perfiles:
        perfiles[usuario_id] = perfil_service().perfil_de(usuario_id)
    return perfiles[usuario_id]


def rol_de_usuario(usuario_id: str) -> str | None:
    """El rol sale de la base, nunca del token: el usuario puede editar su user_metadata."""
    perfil = _perfil_en_peticion(usuario_id)
    return perfil["rol"] if perfil else None


def estado_de_usuario(usuario_id: str) -> str | None:
    return estado_de_cuenta(_perfil_en_peticion(usuario_id))


@lru_cache
def terminos_service() -> TerminosService:
    return TerminosService(session_scope, SqlTerminosRepository())


def _version_de_terminos_en_peticion() -> int:
    """La version vigente se lee una vez por peticion (como el perfil)."""
    if not has_app_context():
        return terminos_service().version_vigente()
    if "version_terminos" not in g:
        g.version_terminos = terminos_service().version_vigente()
    return g.version_terminos


def terminos_pendientes_de(usuario_id: str) -> bool:
    """True si la cuenta no ha aceptado la version vigente de los terminos (HU-B-411)."""
    perfil = _perfil_en_peticion(usuario_id)
    return terminos_pendientes(perfil, _version_de_terminos_en_peticion()) if perfil else False


# --- Contenido editable (HU-B-309): un servicio generico configurado por tipo ---
@lru_cache
def leccion_contenido_service() -> ContenidoService:
    repositorio = SqlContenidoRepository(
        Leccion,
        columna_texto=Leccion.titulo,
        filtros=("estado", "bloque_id"),
        en_uso=lambda i: exists().where(ProgresoLeccion.leccion_id == i),
    )
    return ContenidoService(
        session_scope,
        repositorio,
        SqlCatalogoRepository(),
        nombre="la lección",
        con_autor=True,
        referencias={"bloque_id": "bloques"},
        en_uso="La lección tiene avance de estudiantes. Archívala para ocultarla sin perderlo.",
    )


@lru_cache
def ejercicio_contenido_service() -> ContenidoService:
    repositorio = SqlContenidoRepository(
        Ejercicio,
        columna_texto=Ejercicio.nombre,
        filtros=("estado", "leccion_id"),
        en_uso=lambda i: exists().where(ProgresoEjercicio.ejercicio_id == i),
    )
    return ContenidoService(
        session_scope,
        repositorio,
        SqlCatalogoRepository(),
        nombre="el ejercicio",
        con_autor=True,
        referencias={"leccion_id": "lecciones"},
        en_uso="El ejercicio tiene avance de estudiantes. Archívalo para ocultarlo sin perderlo.",
    )


@lru_cache
def bloque_contenido_service() -> ContenidoService:
    repositorio = SqlContenidoRepository(
        Bloque,
        columna_texto=Bloque.titulo,
        filtros=("estado",),
        en_uso=lambda i: (
            exists().where(Leccion.bloque_id == i) | exists().where(Evaluacion.bloque_id == i)
        ),
    )
    return ContenidoService(
        session_scope,
        repositorio,
        SqlCatalogoRepository(),
        nombre="el bloque",
        con_autor=False,
        referencias={},
        en_uso="El bloque tiene lecciones o evaluaciones. Archívalo en lugar de borrarlo.",
    )


@lru_cache
def gestion_evaluacion_service() -> GestionEvaluacionService:
    return GestionEvaluacionService(
        session_scope, SqlGestionEvaluacionRepository(), curso_service()
    )


@lru_cache
def codigo_service() -> CodigoService:
    secreto = get_settings().codigos_secreto.get_secret_value().encode()
    return CodigoService(SqlCodigoRepository(), secreto)


@lru_cache
def verificacion_service() -> VerificacionService:
    return VerificacionService(
        session_scope, SqlCuentaRepository(), codigo_service(), correo_service()
    )


@lru_cache
def recuperacion_service() -> RecuperacionService:
    return RecuperacionService(
        session_scope,
        SqlCuentaRepository(),
        codigo_service(),
        correo_service(),
        origen_frontend=get_settings().origen_frontend,
    )


@lru_cache
def auth_service() -> AuthService:
    return AuthService(ClienteSupabaseAuth(), verificacion_service(), estado_de_usuario)


@lru_cache
def admin_cuentas_service() -> AdminCuentasService:
    def progreso_de(usuario_id: str) -> dict:
        # ProgresoService solo usa el id del usuario para el resumen.
        return progreso_service().resumen(CurrentUser(id=usuario_id, email=None, token=""))

    return AdminCuentasService(
        session_scope,
        SqlAdminCuentasRepository(),
        SqlCuentaRepository(),
        codigo_service(),
        correo_service(),
        SqlAccionAdminRepository(),
        progreso_de,
    )


@lru_cache
def admin_cursos_service() -> AdminCursosService:
    return AdminCursosService(
        session_scope,
        SqlAdminDocentesRepository(),
        SqlAdminCuentasRepository(),
        SqlCursoRepository(),
        SqlSeguimientoRepository(),
        SqlAccionAdminRepository(),
    )


@lru_cache
def progreso_docente_service() -> ProgresoDocenteService:
    return ProgresoDocenteService(
        session_scope,
        SqlProgresoDocenteRepository(),
        SqlRutaRepository(),
        SqlSeguimientoRepository(),
        curso_service(),
    )


@lru_cache
def mensajeria_service() -> MensajeriaService:
    return MensajeriaService(session_scope, SqlMensajeriaRepository())


@lru_cache
def cuenta_service() -> CuentaService:
    return CuentaService(
        session_scope,
        SqlCuentaRepository(),
        codigo_service(),
        correo_service(),
        ClienteSupabaseAuth(),
    )


# --- Correo saliente (HU-B-401) ---
REMITENTE_LOCAL = "no-responder@sipesound.local"


def _crear_enviador() -> Enviador:
    ajustes = get_settings()
    if ajustes.modo_correo == "archivo":
        return EnviadorArchivo()
    # La configuracion ya garantizo que estos valores existen (Settings._validar_correo).
    return EnviadorSmtp(
        host=ajustes.smtp_host,
        puerto=ajustes.smtp_puerto,
        usuario=ajustes.smtp_usuario or "",
        clave=ajustes.smtp_clave_aplicacion.get_secret_value()
        if ajustes.smtp_clave_aplicacion
        else "",
    )


@lru_cache
def correo_service() -> CorreoService:
    ajustes = get_settings()
    return CorreoService(
        session_scope,
        SqlEnvioCorreoRepository(),
        _crear_enviador(),
        # Dos hilos bastan: los correos son transaccionales (codigos, enlaces y avisos).
        ThreadPoolExecutor(max_workers=2, thread_name_prefix="correo"),
        remitente=ajustes.remitente_correo or REMITENTE_LOCAL,
        nombre_remitente=ajustes.correo_nombre_remitente or MARCA,
    )
