from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models.docente_preautorizado import DocentePreautorizado
from app.repositories.base import Fila
from app.repositories.sqlalchemy._comun import a_fila

# Aplica la preautorizacion a una cuenta YA confirmada con ese correo (si existe).
# La logica vive en la base (revision 0014) para que el trigger y la API hagan lo mismo.
APLICAR_A_CUENTA_EXISTENTE = text(
    "select public.aplicar_docente_preautorizado(u.id, u.email) "
    "from auth.users u where lower(u.email) = :email and u.email_confirmed_at is not null"
)


class SqlDocenteRepository:
    """No abre ni confirma transacciones: usa la sesion del servicio."""

    def obtener(self, sesion: Session, email: str) -> Fila | None:
        fila = sesion.get(DocentePreautorizado, email)
        return a_fila(fila) if fila else None

    def listar(self, sesion: Session) -> list[Fila]:
        consulta = select(DocentePreautorizado).order_by(DocentePreautorizado.creado_en.desc())
        return [a_fila(f) for f in sesion.scalars(consulta)]

    def crear(self, sesion: Session, email: str, creado_por: str) -> Fila:
        fila = DocentePreautorizado(email=email, creado_por=creado_por)
        sesion.add(fila)
        sesion.flush()
        sesion.execute(APLICAR_A_CUENTA_EXISTENTE, {"email": email})
        sesion.refresh(fila)
        return a_fila(fila)

    def eliminar(self, sesion: Session, email: str) -> None:
        sesion.delete(sesion.get(DocentePreautorizado, email))
        sesion.flush()
