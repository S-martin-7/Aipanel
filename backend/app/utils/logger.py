"""
Sistema de logging configurado.

Configura logging estructurado para toda la aplicación.
Los logs se guardan en backend/logs/
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from datetime import datetime

from app.core.config import settings


def setup_logging() -> None:
    """
    Configurar sistema de logging.

    Crea:
    - Handler para consola (stdout)
    - Handler para archivo app.log (rotación automática)
    - Handler para archivo error.log (solo errores)
    """

    # Crear directorio de logs si no existe
    log_dir = Path(settings.LOG_FILE_PATH)
    log_dir.mkdir(parents=True, exist_ok=True)

    # Configurar formato
    log_format = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))

    # Limpiar handlers existentes
    root_logger.handlers.clear()

    # 1. Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_format)
    root_logger.addHandler(console_handler)

    # 2. App log file handler (todos los logs)
    app_handler = RotatingFileHandler(
        filename=log_dir / "app.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding="utf-8"
    )
    app_handler.setFormatter(log_format)
    root_logger.addHandler(app_handler)

    # 3. Error log file handler (solo errores)
    error_handler = RotatingFileHandler(
        filename=log_dir / "error.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding="utf-8"
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(log_format)
    root_logger.addHandler(error_handler)

    # Silenciar logs verbose de librerías
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Obtener logger configurado.

    Args:
        name: Nombre del logger (usualmente __name__ del módulo)

    Returns:
        logging.Logger: Logger configurado
    """
    return logging.getLogger(name)


def log_exception(logger: logging.Logger, exc: Exception, context: str = "") -> None:
    """
    Loguear excepción con contexto.

    Args:
        logger: Logger a usar
        exc: Excepción a loguear
        context: Contexto adicional
    """
    error_msg = f"Exception in {context}: {type(exc).__name__}: {str(exc)}"
    logger.error(error_msg, exc_info=True)

    # Guardar stack trace en archivo de errores
    error_dir = Path("backend/errors/exceptions")
    error_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    error_file = error_dir / f"error_{timestamp}.txt"

    with open(error_file, "w", encoding="utf-8") as f:
        f.write(f"Timestamp: {datetime.now().isoformat()}\n")
        f.write(f"Context: {context}\n")
        f.write(f"Exception Type: {type(exc).__name__}\n")
        f.write(f"Exception Message: {str(exc)}\n\n")

        import traceback
        f.write("Stack Trace:\n")
        f.write(traceback.format_exc())
