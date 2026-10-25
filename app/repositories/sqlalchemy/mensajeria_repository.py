# =========================================================
# Mensajeria interna (HU-B-409). SQL directo: la bandeja, el hilo y el envio a grupos son
# consultas agregadas (un solo INSERT ... SELECT copia los destinatarios de un grupo).
# Usa la sesion del servicio. Nunca selecciona correos.
# =========================================================
import uuid

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.constants import (
    ALCANCE_CURSO,
    ALCANCE_ESTUDIANTES_DOCENTE,
    ALCANCE_ROL_ADMIN,
    ALCANCE_ROL_DOCENTE,
    ALCANCE_ROL_ESTUDIANTE,
    ALCANCE_TODOS,
    ALCANCE_USUARIO,
)
from app.repositories.base import Fila
from app.repositories.sqlalchemy._comun import filas_sql
from app.repositories.sqlalchemy.admin_cuentas_repository import _escapar_like

# Una cuenta "activa" tiene el correo verificado y no esta suspendida: solo ellas reciben.
ACTIVA = "p.correo_verificado_en is not null and p.suspendido_en is null"

# De donde sale cada grupo de destinatarios (siempre columna `id`).
FUENTES = {
    ALCANCE_USUARIO: "select cast(:destinatario as uuid) as id",
    ALCANCE_CURSO: (
        "select i.estudiante_id as id from public.inscripciones i where i.curso_id = :curso"
    ),
    ALCANCE_ESTUDIANTES_DOCENTE: (
        "select distinct i.estudiante_id as id from public.inscripciones i"
        " join public.cursos c on c.id = i.curso_id"
        " where c.docente_id = cast(:remitente as uuid) and c.archivado_en is null"
    ),
    ALCANCE_ROL_ESTUDIANTE: "select p.id from public.profiles p where p.rol = 'estudiante'",
    ALCANCE_ROL_DOCENTE: "select p.id from public.profiles p where p.rol = 'docente'",
    ALCANCE_ROL_ADMIN: "select p.id from public.profiles p where p.rol = 'admin'",
    ALCANCE_TODOS: "select p.id from public.profiles p",
}

# Dos personas "se conocen" si el estudiante esta inscrito en un curso ACTIVO del docente.
COMPARTEN_CURSO = """
select 1 from public.inscripciones i join public.cursos c on c.id = i.curso_id
where c.docente_id = cast(:docente as uuid) and i.estudiante_id = cast(:estudiante as uuid)
  and c.archivado_en is null
limit 1
"""

BANDEJA = """
with mios as (
  select m.id, m.hilo_id, m.asunto, m.cuerpo, m.alcance, m.curso_id, m.remitente_id,
         m.creado_en, d.leido_en, d.archivado_en
  from public.mensaje_destinatarios d
  join public.mensajes m on m.id = d.mensaje_id
  where d.destinatario_id = cast(:u as uuid)
),
hilos as (
  select hilo_id,
    max(creado_en) as ultima_fecha,
    (count(*) filter (where leido_en is null))::int as no_leidos,
    bool_and(archivado_en is not null) as archivado,
    bool_or(remitente_id is distinct from cast(:u as uuid)) as hay_recibidos,
    bool_or(remitente_id = cast(:u as uuid)) as hay_enviados
  from mios group by hilo_id
),
ultimo as (
  select distinct on (hilo_id) hilo_id, asunto, alcance, curso_id, remitente_id,
         left(cuerpo, :extracto) as extracto, creado_en
  from mios order by hilo_id, creado_en desc, id desc
)
select h.hilo_id, u.asunto, u.alcance, c.nombre as curso, h.no_leidos, h.archivado,
       u.creado_en as ultimo_creado_en, u.extracto as ultimo_extracto,
       u.remitente_id is not distinct from cast(:u as uuid) as ultimo_propio,
       r.nombre as ultimo_nombre, r.apellido as ultimo_apellido, r.rol as ultimo_rol,
       count(*) over () as total_filas
from hilos h
join ultimo u on u.hilo_id = h.hilo_id
left join public.profiles r on r.id = u.remitente_id
left join public.cursos c on c.id = u.curso_id
where {filtro}
  and (cast(:q as text) is null or u.asunto ilike :patron)
order by h.ultima_fecha desc, h.hilo_id
limit :limite offset :desde
"""  # noqa: S608 - solo fragmentos constantes; los datos van como parametros

FILTROS = {
    "recibidos": "h.hay_recibidos and not h.archivado",
    "enviados": "h.hay_enviados and not h.archivado",
    "no_leidos": "h.no_leidos > 0 and not h.archivado",
    "archivados": "h.archivado",
}

HILO = """
select m.id, m.remitente_id, m.asunto, m.cuerpo, m.alcance, m.creado_en, d.leido_en,
       c.nombre as curso, r.nombre as remitente_nombre, r.apellido as remitente_apellido,
       r.rol as remitente_rol
from public.mensaje_destinatarios d
join public.mensajes m on m.id = d.mensaje_id
left join public.profiles r on r.id = m.remitente_id
left join public.cursos c on c.id = m.curso_id
where d.destinatario_id = cast(:u as uuid) and m.hilo_id = cast(:h as uuid)
order by m.creado_en, m.id
"""

DOCENTES_DE_ESTUDIANTE = """
select d.id, d.nombre, d.apellido, string_agg(distinct c.nombre, ', ') as detalle
from public.inscripciones i
join public.cursos c on c.id = i.curso_id and c.archivado_en is null
join public.profiles d on d.id = c.docente_id
where i.estudiante_id = cast(:u as uuid)
  and (cast(:q as text) is null or d.nombre ilike :patron or d.apellido ilike :patron
       or c.nombre ilike :patron)
  and d.correo_verificado_en is not null and d.suspendido_en is null
group by d.id, d.nombre, d.apellido
order by d.nombre, d.apellido nulls last, d.id
limit :limite
"""

CURSOS_DE_DOCENTE = """
select c.id, c.nombre,
       (select count(*) from public.inscripciones i where i.curso_id = c.id)::int as estudiantes
from public.cursos c
where c.docente_id = cast(:u as uuid) and c.archivado_en is null
  and (cast(:q as text) is null or c.nombre ilike :patron)
order by c.nombre, c.id
limit :limite
"""

ESTUDIANTES_DE_DOCENTE = f"""
select p.id, p.nombre, p.apellido, string_agg(distinct c.nombre, ', ') as detalle
from public.inscripciones i
join public.cursos c on c.id = i.curso_id and c.archivado_en is null
join public.profiles p on p.id = i.estudiante_id
where c.docente_id = cast(:u as uuid)
  and (p.nombre ilike :patron or p.apellido ilike :patron)
  and {ACTIVA}
group by p.id, p.nombre, p.apellido
order by p.nombre, p.apellido nulls last, p.id
limit :limite
"""  # noqa: S608 - solo fragmentos constantes

PERSONAS = f"""
select p.id, p.nombre, p.apellido, p.rol
from public.profiles p
where p.id <> cast(:u as uuid)
  and p.rol = any(cast(:roles as text[]))
  and (p.nombre ilike :patron or p.apellido ilike :patron)
  and {ACTIVA}
order by p.nombre, p.apellido nulls last, p.id
limit :limite
"""  # noqa: S608 - solo fragmentos constantes


class SqlMensajeriaRepository:
    """No abre ni confirma transacciones: usa la sesion del servicio."""

    # --- Reglas de destino ----------------------------------------------------------------
    def perfil_basico(self, sesion: Session, usuario_id: str) -> Fila | None:
        sql = f"select p.id, p.rol, ({ACTIVA}) as activa from public.profiles p where p.id = cast(:u as uuid)"  # noqa: S608, E501
        filas = filas_sql(sesion, sql, {"u": usuario_id})
        return filas[0] if filas else None

    def comparten_curso_activo(self, sesion: Session, docente_id: str, estudiante_id: str) -> bool:
        parametros = {"docente": docente_id, "estudiante": estudiante_id}
        return bool(filas_sql(sesion, COMPARTEN_CURSO, parametros))

    def curso_activo_de_docente(self, sesion: Session, curso_id: int, docente_id: str) -> bool:
        sql = (
            "select 1 from public.cursos where id = :c and docente_id = cast(:d as uuid)"
            " and archivado_en is null"
        )
        return bool(filas_sql(sesion, sql, {"c": curso_id, "d": docente_id}))

    def mensaje_recibido(self, sesion: Session, mensaje_id: str, usuario_id: str) -> Fila | None:
        """Un mensaje que la persona RECIBIO (no uno que envio): el unico que se puede responder."""
        sql = (
            "select m.id, m.remitente_id, m.asunto, m.hilo_id from public.mensajes m"
            " join public.mensaje_destinatarios d on d.mensaje_id = m.id"
            " where m.id = cast(:m as uuid) and d.destinatario_id = cast(:u as uuid)"
            " and m.remitente_id is distinct from cast(:u as uuid)"
        )
        filas = filas_sql(sesion, sql, {"m": mensaje_id, "u": usuario_id})
        return filas[0] if filas else None

    def contar_enviados_ultima_hora(self, sesion: Session, usuario_id: str) -> tuple[int, int]:
        """(todos, avisos de grupo) enviados en la ultima hora; el limite lo mide la base."""
        sql = (
            "select count(*)::int as total, (count(*) filter (where alcance <> 'usuario'))::int"
            " as avisos from public.mensajes where remitente_id = cast(:u as uuid)"
            " and creado_en > now() - interval '1 hour'"
        )
        fila = filas_sql(sesion, sql, {"u": usuario_id})[0]
        return fila["total"], fila["avisos"]

    # --- Envio ----------------------------------------------------------------------------
    def crear(  # noqa: PLR0913
        self,
        sesion: Session,
        *,
        remitente_id: str,
        asunto: str,
        cuerpo: str,
        alcance: str,
        curso_id: int | None,
        respuesta_a_id: str | None,
        hilo_id: str | None,
    ) -> Fila:
        mensaje_id = str(uuid.uuid4())
        sql = (
            "insert into public.mensajes (id, remitente_id, asunto, cuerpo, alcance, curso_id,"
            " respuesta_a_id, hilo_id) values (cast(:id as uuid), cast(:r as uuid), :a, :c, :al,"
            " :curso, cast(:resp as uuid), cast(:hilo as uuid))"
        )
        sesion.execute(
            text(sql),
            {
                "id": mensaje_id,
                "r": remitente_id,
                "a": asunto,
                "c": cuerpo,
                "al": alcance,
                "curso": curso_id,
                "resp": respuesta_a_id,
                # El primer mensaje de un hilo es la raiz: hilo_id = id.
                "hilo": hilo_id or mensaje_id,
            },
        )
        return {"id": mensaje_id, "hilo_id": hilo_id or mensaje_id}

    def agregar_destinatarios(  # noqa: PLR0913
        self,
        sesion: Session,
        mensaje_id: str,
        *,
        alcance: str,
        remitente_id: str,
        destinatario_id: str | None,
        curso_id: int | None,
    ) -> int:
        """Un solo INSERT ... SELECT copia el grupo EN ESTE MOMENTO. Solo cuentas activas y
        nunca el remitente. Devuelve cuantas personas recibieron el mensaje."""
        sql = (
            "insert into public.mensaje_destinatarios (mensaje_id, destinatario_id)"  # noqa: S608
            f" select cast(:m as uuid), p.id from ({FUENTES[alcance]}) f"
            " join public.profiles p on p.id = f.id"
            f" where {ACTIVA} and p.id <> cast(:remitente as uuid)"
            " on conflict do nothing returning destinatario_id"
        )
        resultado = sesion.execute(
            text(sql),
            {
                "m": mensaje_id,
                "remitente": remitente_id,
                "destinatario": destinatario_id,
                "curso": curso_id,
            },
        )
        return len(resultado.all())

    def agregar_remitente(self, sesion: Session, mensaje_id: str, remitente_id: str) -> None:
        """El remitente ve su propio hilo (y le llegan las respuestas), ya marcado como leido."""
        sesion.execute(
            text(
                "insert into public.mensaje_destinatarios (mensaje_id, destinatario_id, leido_en)"
                " values (cast(:m as uuid), cast(:r as uuid), now()) on conflict do nothing"
            ),
            {"m": mensaje_id, "r": remitente_id},
        )

    # --- Bandeja e hilos ------------------------------------------------------------------
    def bandeja(  # noqa: PLR0913
        self,
        sesion: Session,
        usuario_id: str,
        *,
        filtro: str,
        q: str | None,
        extracto: int,
        pagina: int,
        por_pagina: int,
    ) -> tuple[list[Fila], int]:
        filas = filas_sql(
            sesion,
            BANDEJA.format(filtro=FILTROS[filtro]),
            {
                "u": usuario_id,
                "q": q,
                "patron": f"%{_escapar_like(q)}%" if q else None,
                "extracto": extracto,
                "limite": por_pagina,
                "desde": (pagina - 1) * por_pagina,
            },
        )
        total = filas[0]["total_filas"] if filas else 0
        for fila in filas:
            fila.pop("total_filas")
        return filas, total

    def hilo(self, sesion: Session, usuario_id: str, hilo_id: str) -> list[Fila]:
        return filas_sql(sesion, HILO, {"u": usuario_id, "h": hilo_id})

    def marcar_hilo_leido(self, sesion: Session, usuario_id: str, hilo_id: str) -> None:
        sesion.execute(
            text(
                "update public.mensaje_destinatarios d set leido_en = now()"
                " from public.mensajes m where d.mensaje_id = m.id and m.hilo_id = cast(:h as uuid)"
                " and d.destinatario_id = cast(:u as uuid) and d.leido_en is null"
            ),
            {"u": usuario_id, "h": hilo_id},
        )

    def archivar_hilo(
        self, sesion: Session, usuario_id: str, hilo_id: str, *, archivado: bool
    ) -> int:
        resultado = sesion.execute(
            text(
                "update public.mensaje_destinatarios d"
                " set archivado_en = case when :a then now() end"
                " from public.mensajes m where d.mensaje_id = m.id and m.hilo_id = cast(:h as uuid)"
                " and d.destinatario_id = cast(:u as uuid) returning d.mensaje_id"
            ),
            {"u": usuario_id, "h": hilo_id, "a": archivado},
        )
        return len(resultado.all())

    def marcar_ultimo_recibido_no_leido(
        self, sesion: Session, usuario_id: str, hilo_id: str
    ) -> bool:
        """Solo el ultimo mensaje RECIBIDO: los propios nunca cuentan como sin leer."""
        resultado = sesion.execute(
            text(
                "update public.mensaje_destinatarios set leido_en = null"
                " where destinatario_id = cast(:u as uuid) and mensaje_id = ("
                "   select m.id from public.mensajes m"
                "   join public.mensaje_destinatarios d on d.mensaje_id = m.id"
                "   where d.destinatario_id = cast(:u as uuid) and m.hilo_id = cast(:h as uuid)"
                "     and m.remitente_id is distinct from cast(:u as uuid)"
                "   order by m.creado_en desc, m.id desc limit 1)"
                " returning mensaje_id"
            ),
            {"u": usuario_id, "h": hilo_id},
        )
        return len(resultado.all()) > 0

    def contar_no_leidos(self, sesion: Session, usuario_id: str) -> int:
        """Para el contador del frontend: usa el indice (destinatario_id, leido_en, mensaje_id)."""
        sql = (
            "select count(*)::int as total from public.mensaje_destinatarios"
            " where destinatario_id = cast(:u as uuid) and leido_en is null"
            " and archivado_en is null"
        )
        return filas_sql(sesion, sql, {"u": usuario_id})[0]["total"]

    # --- Busqueda de destinatarios --------------------------------------------------------
    @staticmethod
    def _patron(q: str | None) -> str | None:
        return f"%{_escapar_like(q)}%" if q else None

    def docentes_de_estudiante(
        self, sesion: Session, usuario_id: str, q: str | None, limite: int
    ) -> list[Fila]:
        parametros = {"u": usuario_id, "q": q, "patron": self._patron(q), "limite": limite}
        return filas_sql(sesion, DOCENTES_DE_ESTUDIANTE, parametros)

    def cursos_de_docente(
        self, sesion: Session, usuario_id: str, q: str | None, limite: int
    ) -> list[Fila]:
        parametros = {"u": usuario_id, "q": q, "patron": self._patron(q), "limite": limite}
        return filas_sql(sesion, CURSOS_DE_DOCENTE, parametros)

    def estudiantes_de_docente(
        self, sesion: Session, usuario_id: str, q: str, limite: int
    ) -> list[Fila]:
        parametros = {"u": usuario_id, "patron": self._patron(q), "limite": limite}
        return filas_sql(sesion, ESTUDIANTES_DE_DOCENTE, parametros)

    def personas(
        self, sesion: Session, usuario_id: str, roles: list[str], q: str, limite: int
    ) -> list[Fila]:
        parametros = {"u": usuario_id, "roles": roles, "patron": self._patron(q), "limite": limite}
        return filas_sql(sesion, PERSONAS, parametros)
