# =========================================================
# Proteccion de datos de estudiantes (menores de edad, Ley 1581 de 2012).
# El docente ve el correo enmascarado: suficiente para reconocerlo, no para usarlo.
# =========================================================


def enmascarar_email(email: str | None) -> str | None:
    """ana.perez@colegio.edu.co -> a***@colegio.edu.co"""
    if not email or "@" not in email:
        return None
    usuario, _, dominio = email.partition("@")
    return f"{usuario[:1]}***@{dominio}"
