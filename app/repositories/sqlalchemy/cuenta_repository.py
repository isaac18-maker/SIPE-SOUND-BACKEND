from sqlalchemy import text
from sqlalchemy.orm import Session

from app.repositories.base import Fila
from app.repositories.sqlalchemy._comun import filas_sql

# Lee auth.users solo para ubicar la cuenta por su correo (como seguimiento_repository).
BUSCAR_PENDIENTE = text(
    "select p.id, p.nombre, u.email "
    "from auth.users u join public.profiles p on p.id = u.id "
    "where lower(u.email) = :email and p.correo_verificado_en is null"
)
BUSCAR_POR_EMAIL = text(
    "select p.id, p.nombre, p.correo_verificado_en is not null as verificada "
    "from auth.users u join public.profiles p on p.id = u.id "
    "where lower(u.email) = :email"
)
BUSCAR_VERIFICADA = text(
    "select p.id, p.nombre, u.email "
    "from auth.users u join public.profiles p on p.id = u.id "
    "where lower(u.email) = :email and p.correo_verificado_en is not null "
    "and p.suspendido_en is null"
)
DATOS_DE_AVISO = text(
    "select p.nombre, u.email from auth.users u join public.profiles p on p.id = u.id "
    "where u.id = :id"
)
# Funciones SECURITY DEFINER de la revision 0021 (EXECUTE solo para el rol del backend).
FIJAR_CONTRASENA = text("select public.fijar_contrasena(cast(:id as uuid), :password)")
CERRAR_SESIONES = text("select public.cerrar_sesiones(cast(:id as uuid), cast(:excepto as uuid))")
CORREO_EN_USO = text(
    "select 1 from auth.users where lower(email) = :email and id <> cast(:excepto as uuid) limit 1"
)
# Funcion SECURITY DEFINER de la revision 0032: Supabase Auth exige email_confirmed_at para
# iniciar sesion, asi que se confirma ahi cuando el backend verifica el correo.
CONFIRMAR_CORREO_AUTH = text("select public.confirmar_correo_auth(cast(:id as uuid))")
# Funcion SECURITY DEFINER de la revision 0022 (EXECUTE solo para el rol del backend).
CAMBIAR_CORREO = text("select public.cambiar_correo(cast(:id as uuid), :email)")
# Funcion SECURITY DEFINER de la revision 0024: se niega con un administrador.
ELIMINAR_CUENTA = text("select public.eliminar_cuenta(cast(:id as uuid))")
# El trigger on_profile_verificado (revision 0019) aplica la preautorizacion de docente.
MARCAR_VERIFICADA = text(
    "update public.profiles set correo_verificado_en = now(), "
    # El registro exige marcar la casilla de terminos (HU-B-323): queda la version vigente.
    "terminos_version = (select version from public.documentos_legales where tipo = 'terminos'), "
    "terminos_aceptados_en = now() "
    "where id = :id and correo_verificado_en is null"
)


class SqlCuentaRepository:
    """No abre ni confirma transacciones: usa la sesion del servicio."""

    def buscar_pendiente_por_email(self, sesion: Session, email: str) -> Fila | None:
        filas = filas_sql(sesion, BUSCAR_PENDIENTE, {"email": email})
        return filas[0] if filas else None

    def buscar_por_email(self, sesion: Session, email: str) -> Fila | None:
        filas = filas_sql(sesion, BUSCAR_POR_EMAIL, {"email": email})
        return filas[0] if filas else None

    def buscar_verificada_por_email(self, sesion: Session, email: str) -> Fila | None:
        filas = filas_sql(sesion, BUSCAR_VERIFICADA, {"email": email})
        return filas[0] if filas else None

    def marcar_verificada(self, sesion: Session, usuario_id: str) -> None:
        sesion.execute(MARCAR_VERIFICADA, {"id": usuario_id})

    def confirmar_en_proveedor(self, sesion: Session, usuario_id: str) -> None:
        sesion.execute(CONFIRMAR_CORREO_AUTH, {"id": usuario_id})

    def datos_de_aviso(self, sesion: Session, usuario_id: str) -> Fila | None:
        filas = filas_sql(sesion, DATOS_DE_AVISO, {"id": usuario_id})
        return filas[0] if filas else None

    def correo_en_uso(self, sesion: Session, email: str, *, excepto_id: str) -> bool:
        fila = sesion.execute(CORREO_EN_USO, {"email": email.lower(), "excepto": excepto_id})
        return fila.first() is not None

    def cambiar_correo(self, sesion: Session, usuario_id: str, email: str) -> None:
        sesion.execute(CAMBIAR_CORREO, {"id": usuario_id, "email": email})

    def eliminar_cuenta(self, sesion: Session, usuario_id: str) -> None:
        sesion.execute(ELIMINAR_CUENTA, {"id": usuario_id})

    def fijar_contrasena(self, sesion: Session, usuario_id: str, password: str) -> None:
        sesion.execute(FIJAR_CONTRASENA, {"id": usuario_id, "password": password})

    def cerrar_sesiones(
        self, sesion: Session, usuario_id: str, *, excepto: str | None = None
    ) -> None:
        sesion.execute(CERRAR_SESIONES, {"id": usuario_id, "excepto": excepto})
