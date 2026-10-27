import math

from sqlalchemy import Interval, case, func, literal_column, select, update
from sqlalchemy.orm import Session

from app.core.constants import CODIGO_INTENTOS_MAX
from app.models.codigo_verificacion import CodigoVerificacion as Codigo
from app.repositories.base import Fila
from app.repositories.sqlalchemy._comun import a_fila

ABIERTO = (Codigo.usado_en.is_(None), Codigo.invalidado_en.is_(None))


def _intervalo(cantidad: int, unidad: str):
    # int(): la cantidad viene de constantes, pero nunca se interpola un valor sin convertir.
    return literal_column(f"interval '{int(cantidad)} {unidad}'", type_=Interval)


class SqlCodigoRepository:
    """No abre ni confirma transacciones: usa la sesion del servicio.

    El tiempo lo mide la base (now()), no el reloj del servidor de la API.
    """

    def invalidar_abiertos(self, sesion: Session, usuario_id: str, proposito: str) -> None:
        sesion.execute(
            update(Codigo)
            .where(Codigo.usuario_id == usuario_id, Codigo.proposito == proposito, *ABIERTO)
            .values(invalidado_en=func.now())
        )

    def crear(
        self,
        sesion: Session,
        *,
        usuario_id: str,
        proposito: str,
        codigo_hash: str,
        email_destino: str | None,
        vigencia_min: int,
    ) -> None:
        sesion.add(
            Codigo(
                usuario_id=usuario_id,
                proposito=proposito,
                codigo_hash=codigo_hash,
                email_destino=email_destino,
                expira_en=func.now() + _intervalo(vigencia_min, "minutes"),
            )
        )
        sesion.flush()

    def hay_reciente(
        self, sesion: Session, usuario_id: str, proposito: str, *, segundos: int
    ) -> bool:
        desde = func.now() - _intervalo(segundos, "seconds")
        consulta = select(Codigo.id).where(
            Codigo.usuario_id == usuario_id,
            Codigo.proposito == proposito,
            Codigo.creado_en >= desde,
        )
        return sesion.scalar(consulta.limit(1)) is not None

    def obtener_abierto_vigente(
        self, sesion: Session, usuario_id: str, proposito: str
    ) -> Fila | None:
        """Bloquea la fila: dos peticiones con el mismo codigo se atienden una tras otra."""
        consulta = (
            select(Codigo)
            .where(
                Codigo.usuario_id == usuario_id,
                Codigo.proposito == proposito,
                Codigo.expira_en > func.now(),
                *ABIERTO,
            )
            .with_for_update()
        )
        fila = sesion.scalar(consulta)
        return a_fila(fila) if fila else None

    def obtener_abierto_por_hash(
        self, sesion: Session, proposito: str, codigo_hash: str
    ) -> Fila | None:
        """Para tokens largos (enlaces): el token identifica a la persona. Bloquea la fila."""
        consulta = (
            select(Codigo)
            .where(
                Codigo.proposito == proposito,
                Codigo.codigo_hash == codigo_hash,
                Codigo.expira_en > func.now(),
                *ABIERTO,
            )
            .with_for_update()
        )
        fila = sesion.scalar(consulta)
        return a_fila(fila) if fila else None

    def segundos_restantes(self, sesion: Session, usuario_id: str, proposito: str) -> int:
        """Segundos que le quedan al codigo abierto mas reciente; 0 si no hay ninguno vigente."""
        consulta = (
            select(func.extract("epoch", Codigo.expira_en - func.now()))
            .where(
                Codigo.usuario_id == usuario_id,
                Codigo.proposito == proposito,
                Codigo.expira_en > func.now(),
                *ABIERTO,
            )
            .order_by(Codigo.creado_en.desc())
            .limit(1)
        )
        restante = sesion.scalar(consulta)
        return max(0, math.ceil(float(restante))) if restante is not None else 0

    def registrar_fallo(self, sesion: Session, codigo_id: str) -> None:
        """Suma un intento; al llegar al maximo el codigo se invalida."""
        sesion.execute(
            update(Codigo)
            .where(Codigo.id == codigo_id)
            .values(
                intentos=Codigo.intentos + 1,
                invalidado_en=case(
                    (Codigo.intentos + 1 >= CODIGO_INTENTOS_MAX, func.now()),
                    else_=Codigo.invalidado_en,
                ),
            )
        )

    def consumir(self, sesion: Session, codigo_id: str) -> bool:
        """UPDATE atomico: solo una peticion recibe la fila, aunque lleguen dos a la vez."""
        resultado = sesion.execute(
            update(Codigo)
            .where(Codigo.id == codigo_id, Codigo.expira_en > func.now(), *ABIERTO)
            .values(usado_en=func.now())
            .returning(Codigo.id)
        )
        return resultado.first() is not None
