import logging
import os
from datetime import datetime


def setup_logger(name: str) -> logging.Logger:
    """Konfiguruje i zwraca logger dla podanego modułu"""
    logger = logging.getLogger(name)

    if not logger.handlers:
        logger.setLevel(logging.INFO)

        # Tworzenie katalogu na logi jeśli nie istnieje
        log_dir = "logs"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        # Handler do pliku
        log_file = os.path.join(log_dir, f"{datetime.now().strftime('%Y%m%d')}.log")
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.INFO)

        # Handler do konsoli
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        # Format logów - tylko sama wiadomość, bez prefixów
        formatter = logging.Formatter("%(message)s")
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger
