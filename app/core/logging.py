import logging

FORMATO = "%(asctime)s %(levelname)s %(name)s: %(message)s"


def configure_logging(nivel: str) -> None:
    logging.basicConfig(level=nivel.upper(), format=FORMATO)
