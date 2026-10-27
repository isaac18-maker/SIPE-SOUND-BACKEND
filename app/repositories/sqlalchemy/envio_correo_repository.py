from sqlalchemy.orm import Session

from app.models.envio_correo import EnvioCorreo


class SqlEnvioCorreoRepository:
    """No abre ni confirma transacciones: usa la sesion del servicio."""

    def registrar(
        self, sesion: Session, *, usuario_id: str | None, tipo: str, estado: str, error: str | None
    ) -> None:
        sesion.add(EnvioCorreo(usuario_id=usuario_id, tipo=tipo, estado=estado, error=error))
        sesion.flush()
