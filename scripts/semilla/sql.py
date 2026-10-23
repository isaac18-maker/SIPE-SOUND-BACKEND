"""Sentencias de la semilla (HU-B-326). Todas usan la sesion (transaccion) del script."""

import json
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.constants import (
    ESTADO_PUBLICADO,
    EVALUACION_PUBLICADA,
    PORCENTAJE_APROBACION,
    ROL_ADMIN,
)

# Contenido y su actividad. Sin CASCADE: si otra tabla dependiera de estas, TRUNCATE falla y la
# transaccion se revierte en lugar de borrar mas de lo previsto.
TABLAS_CONTENIDO = (
    "intentos_evaluacion",
    "preguntas_evaluacion",
    "evaluaciones",
    "retroalimentaciones",
    "inscripciones",
    "curso_bloques",
    "cursos",
    "progreso_lecciones",
    "progreso_ejercicios",
    "ejercicios",
    "lecciones",
    "bloques",
)
TABLAS_CONTEO = (*TABLAS_CONTENIDO, "acordes", "profiles")
INSTANCIA = "00000000-0000-0000-0000-000000000000"


def conteos(sesion: Session) -> dict[str, int]:
    return {
        t: sesion.execute(text(f"select count(*) from public.{t}")).scalar_one()  # noqa: S608 - nombres constantes
        for t in TABLAS_CONTEO
    }


def promover_admin(sesion: Session, email: str) -> str:
    fila = sesion.execute(
        text("select id from auth.users where lower(email) = lower(:email)"), {"email": email}
    ).first()
    if fila is None:
        raise SystemExit(f"No existe una cuenta con el correo {email}: no se hizo nada.")
    sesion.execute(
        text("update public.profiles set rol = :rol where id = :id"),
        {"rol": ROL_ADMIN, "id": fila.id},
    )
    return str(fila.id)


def vaciar_contenido(sesion: Session) -> None:
    sesion.execute(text(f"truncate {', '.join(TABLAS_CONTENIDO)} restart identity"))


def cuenta_de_prueba(
    sesion: Session, datos: dict[str, str], clave: str, rol: str, admin_id: str
) -> str:
    """Crea (o restablece) una cuenta confirmada sin enviar correos, como las semillas de
    Supabase. El trigger handle_new_user crea su perfil."""
    email = datos["email"].lower()
    if rol == "docente":
        sesion.execute(
            text(
                "insert into public.docentes_preautorizados (email, creado_por) "
                "values (:email, :admin) on conflict (email) do nothing"
            ),
            {"email": email, "admin": admin_id},
        )
    existente = sesion.execute(
        text("select id from auth.users where lower(email) = :email"), {"email": email}
    ).scalar()
    if existente:
        sesion.execute(
            text(
                "update auth.users set encrypted_password = "
                "extensions.crypt(:clave, extensions.gen_salt('bf')), "
                "email_confirmed_at = coalesce(email_confirmed_at, now()), updated_at = now() "
                "where id = :id"
            ),
            {"clave": clave, "id": existente},
        )
        usuario_id = str(existente)
    else:
        usuario_id = _crear_usuario(sesion, email, datos["nombre"], clave)
    sesion.execute(
        text("update public.profiles set rol = :rol, nombre = :nombre where id = :id"),
        {"rol": rol, "nombre": datos["nombre"], "id": usuario_id},
    )
    if rol == "docente":
        sesion.execute(
            text(
                "update public.docentes_preautorizados set usado_en = now(), usuario_id = :id "
                "where email = :email and usado_en is null"
            ),
            {"id": usuario_id, "email": email},
        )
    return usuario_id


def _crear_usuario(sesion: Session, email: str, nombre: str, clave: str) -> str:
    usuario_id = sesion.execute(
        text(
            "insert into auth.users (instance_id, id, aud, role, email, encrypted_password, "
            "email_confirmed_at, raw_app_meta_data, raw_user_meta_data, created_at, updated_at, "
            "confirmation_token, recovery_token, email_change, email_change_token_new) "
            "values (:instancia, gen_random_uuid(), 'authenticated', 'authenticated', :email, "
            "extensions.crypt(:clave, extensions.gen_salt('bf')), now(), "
            '\'{"provider": "email", "providers": ["email"]}\'::jsonb, '
            "jsonb_build_object('nombre', cast(:nombre as text)), now(), now(), '', '', '', '') "
            "returning id"
        ),
        {"instancia": INSTANCIA, "email": email, "clave": clave, "nombre": nombre},
    ).scalar_one()
    sesion.execute(
        text(
            "insert into auth.identities (provider_id, user_id, identity_data, provider, "
            "last_sign_in_at, created_at, updated_at) "
            "values (cast(:id as text), :id, jsonb_build_object('sub', cast(:id as text), "
            "'email', cast(:email as text), 'email_verified', true), 'email', now(), now(), now())"
        ),
        {"id": usuario_id, "email": email},
    )
    return str(usuario_id)


def insertar_ruta(sesion: Session, bloques: list[dict[str, Any]], *, autor_id: str) -> dict:
    """Bloques en orden, lecciones numeradas en orden global, ejercicios y una evaluacion
    global publicada por bloque. Devuelve los ids para cursos y progreso."""
    ids: dict[str, Any] = {"bloques": [], "lecciones": {}, "ejercicios": [], "evaluaciones": []}
    numero = 0
    for posicion, bloque in enumerate(bloques, start=1):
        bloque_id = _insertar(
            sesion,
            "bloques",
            numero=posicion,
            titulo=bloque["titulo"],
            descripcion=bloque["descripcion"],
            nivel=bloque["nivel"],
            orden_index=posicion,
            estado=ESTADO_PUBLICADO,
        )
        ids["bloques"].append(bloque_id)
        for leccion in bloque["lecciones"]:
            numero += 1
            ids["lecciones"][numero] = _insertar_leccion(
                sesion, leccion, numero, bloque, bloque_id=bloque_id, autor_id=autor_id
            )
        for ejercicio in bloque["ejercicios"]:
            ids["ejercicios"].append(_insertar_ejercicio(sesion, ejercicio, bloque, ids, autor_id))
        ids["evaluaciones"].append(
            _insertar_evaluacion(sesion, posicion, bloque, bloque_id, autor_id)
        )
    return ids


def _insertar_leccion(
    sesion: Session, leccion: dict, numero: int, bloque: dict, *, bloque_id: int, autor_id: str
) -> int:
    return _insertar(
        sesion,
        "lecciones",
        numero=numero,
        titulo=leccion["titulo"],
        descripcion=leccion["descripcion"],
        nivel=bloque["nivel"],
        acordes=leccion["acordes"],
        temas=leccion["temas"],
        contenido=leccion["contenido"],
        bloque_id=bloque_id,
        estado=ESTADO_PUBLICADO,
        autor_id=autor_id,
        duracion_min=leccion["duracion_min"],
    )


def _insertar_ejercicio(
    sesion: Session, ejercicio: dict, bloque: dict, ids: dict, autor_id: str
) -> int:
    return _insertar(
        sesion,
        "ejercicios",
        leccion_id=ids["lecciones"][ejercicio["leccion"]],
        nombre=ejercicio["nombre"],
        descripcion=ejercicio["descripcion"],
        nivel=bloque["nivel"],
        bpm_recomendado=ejercicio["bpm"],
        compas=ejercicio["compas"],
        acordes=ejercicio["acordes"],
        pasos=ejercicio["pasos"],
        estado=ESTADO_PUBLICADO,
        autor_id=autor_id,
        duracion_min=ejercicio["duracion_min"],
    )


def _insertar_evaluacion(
    sesion: Session, posicion: int, bloque: dict, bloque_id: int, autor_id: str
) -> int:
    preguntas = bloque["evaluacion"]
    evaluacion_id = _insertar(
        sesion,
        "evaluaciones",
        titulo=f"Evaluación del bloque {posicion}: {bloque['titulo']}",
        descripcion=f"{len(preguntas)} preguntas. Apruebas con {PORCENTAJE_APROBACION} %.",
        bloque_id=bloque_id,
        autor_id=autor_id,
        porcentaje_aprobacion=PORCENTAJE_APROBACION,
        estado=EVALUACION_PUBLICADA,
    )
    for orden, pregunta in enumerate(preguntas, start=1):
        sesion.execute(
            text(
                "insert into public.preguntas_evaluacion "
                "(evaluacion_id, enunciado, opciones, respuesta_correcta, orden) "
                "values (:evaluacion, :enunciado, cast(:opciones as jsonb), :correcta, :orden)"
            ),
            {
                "evaluacion": evaluacion_id,
                "enunciado": pregunta["enunciado"],
                "opciones": json.dumps(pregunta["opciones"], ensure_ascii=False),
                "correcta": pregunta["correcta"],
                "orden": orden,
            },
        )
    return evaluacion_id


def insertar_cursos(
    sesion: Session, cursos: list[dict], ids: dict, *, docente_id: str, estudiante_id: str
) -> None:
    for curso in cursos:
        curso_id = _insertar(
            sesion,
            "cursos",
            nombre=curso["nombre"],
            descripcion=curso["descripcion"],
            docente_id=docente_id,
            nivel=curso["nivel"],
            codigo_invitacion=curso["codigo"],
        )
        for orden, posicion in enumerate(curso["ruta"], start=1):
            sesion.execute(
                text(
                    "insert into public.curso_bloques (curso_id, bloque_id, orden) "
                    "values (:c, :b, :o)"
                ),
                {"c": curso_id, "b": ids["bloques"][posicion - 1], "o": orden},
            )
        if curso["inscribir_estudiante"]:
            sesion.execute(
                text("insert into public.inscripciones (curso_id, estudiante_id) values (:c, :e)"),
                {"c": curso_id, "e": estudiante_id},
            )
        if curso["retroalimentacion"]:
            sesion.execute(
                text(
                    "insert into public.retroalimentaciones "
                    "(curso_id, estudiante_id, docente_id, mensaje) "
                    "values (:c, :e, :d, :m)"
                ),
                {
                    "c": curso_id,
                    "e": estudiante_id,
                    "d": docente_id,
                    "m": curso["retroalimentacion"],
                },
            )


def insertar_progreso_demo(sesion: Session, demo: dict, ids: dict, *, estudiante_id: str) -> None:
    """Avance de demostracion de la cuenta de prueba (no de personas reales)."""
    for numero, dias in demo["lecciones"].items():
        sesion.execute(
            text(
                "insert into public.progreso_lecciones "
                "(estudiante_id, leccion_id, porcentaje, completado, creado_en, actualizado_en) "
                "values (:e, :l, 100, true, now() - make_interval(days => :d), "
                "now() - make_interval(days => :d))"
            ),
            {"e": estudiante_id, "l": ids["lecciones"][numero], "d": dias},
        )
    for posicion, avance in demo["ejercicios"].items():
        sesion.execute(
            text(
                "insert into public.progreso_ejercicios (estudiante_id, ejercicio_id, porcentaje, "
                "completado, mejor_bpm, creado_en, actualizado_en) values (:e, :j, :p, :c, :b, "
                "now() - make_interval(days => :d), now() - make_interval(days => :d))"
            ),
            {
                "e": estudiante_id,
                "j": ids["ejercicios"][posicion - 1],
                "p": avance["porcentaje"],
                "c": avance["completado"],
                "b": avance["mejor_bpm"],
                "d": avance["dias"],
            },
        )
    for posicion, intentos in demo["intentos"].items():
        for dias, correctas in intentos:
            puntaje = round(correctas * 100 / 5)
            sesion.execute(
                text(
                    "insert into public.intentos_evaluacion (evaluacion_id, estudiante_id, "
                    "puntaje, correctas, total, aprobado, creado_en) "
                    "values (:v, :e, :p, :c, 5, :a, "
                    "now() - make_interval(days => :d))"
                ),
                {
                    "v": ids["evaluaciones"][posicion - 1],
                    "e": estudiante_id,
                    "p": puntaje,
                    "c": correctas,
                    "a": puntaje >= PORCENTAJE_APROBACION,
                    "d": dias,
                },
            )


def _insertar(sesion: Session, tabla: str, **valores: Any) -> int:
    columnas = ", ".join(valores)
    marcadores = ", ".join(f":{c}" for c in valores)
    sentencia = f"insert into public.{tabla} ({columnas}) values ({marcadores}) returning id"  # noqa: S608 - tabla y columnas constantes del script
    return sesion.execute(text(sentencia), valores).scalar_one()
