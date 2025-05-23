import logging
import os
from datetime import datetime
from typing import Optional


def setup_logger(
    name: str, log_to_file: bool = False, log_file_path: Optional[str] = None
) -> logging.Logger:
    """Konfiguruje i zwraca logger dla podanego modułu"""
    logger = logging.getLogger(name)

    # Usuń istniejące handlery, aby uniknąć duplikowania
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    logger.setLevel(logging.INFO)

    # Handler do konsoli - zawsze aktywny
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # Format logów z czasem i nazwą modułu
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(message)s", datefmt="%H:%M:%S"
    )
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Handler do pliku - tylko jeśli włączony w preferencjach
    if log_to_file:
        # Tworzenie katalogu na logi jeśli nie istnieje
        log_dir = "logs"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        # Użyj podanej ścieżki lub domyślnej
        if log_file_path:
            file_path = log_file_path
        else:
            file_path = os.path.join(
                log_dir, f"{datetime.now().strftime('%Y%m%d')}.log"
            )

        file_handler = logging.FileHandler(file_path, encoding="utf-8")
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger
