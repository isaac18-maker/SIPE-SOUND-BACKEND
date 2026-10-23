import inspect
import re
from typing import Any

from flask import Flask, jsonify
from flask_swagger_ui import get_swaggerui_blueprint
from werkzeug.routing import Rule

RUTA_PARAMETRO = re.compile(r"<(?:(?P<convertidor>[^:<>]+):)?(?P<nombre>[^<>]+)>")
TIPOS_PARAMETRO = {"int": "integer", "uuid": "string"}
METODOS_ESCRITURA = {"POST", "PUT", "PATCH"}
METODOS_IGNORADOS = {"HEAD", "OPTIONS"}


def _convertir_ruta(ruta: str) -> str:
    return RUTA_PARAMETRO.sub(r"{\g<nombre>}", ruta)


def _parametros_ruta(regla: Rule) -> list[dict[str, Any]]:
    parametros = []
    for coincidencia in RUTA_PARAMETRO.finditer(regla.rule):
        convertidor = coincidencia.group("convertidor")
        tipo = TIPOS_PARAMETRO.get(convertidor, "string")
        esquema: dict[str, str] = {"type": tipo}
        if convertidor == "uuid":
            esquema["format"] = "uuid"
        parametros.append(
            {
                "name": coincidencia.group("nombre"),
                "in": "path",
                "required": True,
                "schema": esquema,
            }
        )
    return parametros


def _resumen_operacion(app: Flask, endpoint: str) -> tuple[str, str | None]:
    vista = app.view_functions[endpoint]
    docstring = inspect.getdoc(vista)
    nombre = endpoint.rsplit(".", maxsplit=1)[-1]
    resumen = docstring.splitlines()[0] if docstring else nombre.replace("_", " ").capitalize()
    descripcion = "\n".join(docstring.splitlines()[1:]).strip() if docstring else None
    return resumen, descripcion or None


def _crear_operacion(app: Flask, regla: Rule, metodo: str) -> dict[str, Any]:
    resumen, descripcion = _resumen_operacion(app, regla.endpoint)
    operacion: dict[str, Any] = {
        "tags": [regla.endpoint.split(".", maxsplit=1)[0].removesuffix("_legado")],
        "summary": resumen,
        "operationId": f"{regla.endpoint.replace('.', '_')}_{metodo.lower()}",
        "responses": {"200": {"description": "Respuesta según el contrato de la API."}},
    }
    if descripcion:
        operacion["description"] = descripcion

    parametros = _parametros_ruta(regla)
    if parametros:
        operacion["parameters"] = parametros
    if metodo in METODOS_ESCRITURA:
        operacion["requestBody"] = {
            "required": True,
            "content": {
                "application/json": {"schema": {"type": "object", "additionalProperties": True}}
            },
        }
    if getattr(app.view_functions[regla.endpoint], "requires_authentication", False):
        operacion["security"] = [{"TokenSupabase": []}]
    return operacion


def generar_especificacion(app: Flask) -> dict[str, Any]:
    rutas: dict[str, dict[str, Any]] = {}
    for regla in app.url_map.iter_rules():
        if not regla.rule.startswith("/api/"):
            continue
        ruta = _convertir_ruta(regla.rule)
        operaciones = rutas.setdefault(ruta, {})
        for metodo in sorted(regla.methods - METODOS_IGNORADOS):
            operaciones[metodo.lower()] = _crear_operacion(app, regla, metodo)

    return {
        "openapi": "3.0.3",
        "info": {
            "title": "SIPE-SOUND API",
            "version": "1.0.0",
            "description": (
                "Documentación de los endpoints activos. Los endpoints bajo /api/v1 "
                "siguen el contrato vigente; /api conserva respuestas legadas."
            ),
        },
        "servers": [{"url": "/"}],
        "paths": rutas,
        "components": {
            "securitySchemes": {
                "TokenSupabase": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT",
                    "description": "Token de acceso emitido por Supabase Auth.",
                }
            }
        },
    }


def registrar_documentacion(app: Flask) -> None:
    @app.get("/openapi.json")
    def obtener_especificacion():
        return jsonify(generar_especificacion(app))

    app.register_blueprint(
        get_swaggerui_blueprint(
            "/docs",
            "/openapi.json",
            config={"app_name": "SIPE-SOUND API"},
        )
    )
