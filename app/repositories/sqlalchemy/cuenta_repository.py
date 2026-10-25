from sqlalchemy import text
from sqlalchemy.orm import Session

from app.repositories.base import Fila

# Lee auth.users solo para ubicar la cuenta por su correo (como seguimiento_repository).
BUSCAR_PENDIENTE = text(
    "select p.id, p.nombre, u.email "
    "from auth.users u join public.profiles p on p.id = u.id "
    "where lower(u.email) = :email and p.correo_verificado_en is null"
)
BUSCAR_VERIFICADA = text(
    "select p.id, p.nombre, u.email "
    "from auth.users u join public.profiles p on p.id = u.id "
    "where lower(u.email) = :email and p.correo_verificado_en is not null"
)
DATOS_DE_AVISO = text(
    "select p.nombre, u.email from auth.users u join public.profiles p on p.id = u.id "
    "where u.id = :id"
)
# Funciones SECURITY DEFINER de la revision 0021 (EXECUTE solo para el rol del backend).
FIJAR_CONTRASENA = text("select public.fijar_contrasena(cast(:id as uuid), :password)")
CERRAR_SESIONES = text("select public.cerrar_sesiones(cast(:id as uuid), cast(:excepto as uuid))")
# El trigger on_profile_verificado (revision 0019) aplica la preautorizacion de docente.
MARCAR_VERIFICADA = text(
    "update public.profiles set correo_verificado_en = now() "
    "where id = :id and correo_verificado_en is null"
)


class SqlCuentaRepository:
    """No abre ni confirma transacciones: usa la sesion del servicio."""

    def buscar_pendiente_por_email(self, sesion: Session, email: str) -> Fila | None:
        fila = sesion.execute(BUSCAR_PENDIENTE, {"email": email}).mappings().first()
        return dict(fila) if fila else None

    def buscar_verificada_por_email(self, sesion: Session, email: str) -> Fila | None:
        fila = sesion.execute(BUSCAR_VERIFICADA, {"email": email}).mappings().first()
        return dict(fila) if fila else None

    def marcar_verificada(self, sesion: Session, usuario_id: str) -> None:
        sesion.execute(MARCAR_VERIFICADA, {"id": usuario_id})

    def datos_de_aviso(self, sesion: Session, usuario_id: str) -> Fila | None:
        fila = sesion.execute(DATOS_DE_AVISO, {"id": usuario_id}).mappings().first()
        return dict(fila) if fila else None

    def fijar_contrasena(self, sesion: Session, usuario_id: str, password: str) -> None:
        sesion.execute(FIJAR_CONTRASENA, {"id": usuario_id, "password": password})

    def cerrar_sesiones(
        self, sesion: Session, usuario_id: str, *, excepto: str | None = None
    ) -> None:
        sesion.execute(CERRAR_SESIONES, {"id": usuario_id, "excepto": excepto})
