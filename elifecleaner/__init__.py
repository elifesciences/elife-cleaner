import logging


__version__ = "0.2.1"


LOGGER = logging.getLogger(__name__)
LOGGER.addHandler(logging.NullHandler())


def configure_logging(filename):
    "configure logging to file"
    handler = logging.FileHandler(filename)
    formatter = logging.Formatter(
        "%(levelname)s %(name)s:%(module)s:%(funcName)s: %(message)s"
    )
    handler.setFormatter(formatter)
    LOGGER.addHandler(handler)
    LOGGER.setLevel(logging.INFO)
