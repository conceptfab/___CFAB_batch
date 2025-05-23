import json
import os
from typing import Dict, Optional


class Config:
    def __init__(self):
        self.config_file = "config.json"
        self.c4d_versions: Dict[str, str] = {}
        self.log_to_file: bool = False
        self.log_file_path: Optional[str] = None
        self.load_config()

    def load_config(self):
        """Ładuje konfigurację z pliku"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.c4d_versions = data.get("c4d_versions", {})
                    self.log_to_file = data.get("log_to_file", False)
                    self.log_file_path = data.get("log_file_path", None)
            except Exception as e:
                print(f"Błąd ładowania konfiguracji: {str(e)}")
                self.c4d_versions = {}
                self.log_to_file = False
                self.log_file_path = None

    def save_config(self):
        """Zapisuje konfigurację do pliku"""
        try:
            data = {
                "c4d_versions": self.c4d_versions,
                "log_to_file": self.log_to_file,
                "log_file_path": self.log_file_path,
            }
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Błąd zapisywania konfiguracji: {str(e)}")

    def get_c4d_versions(self) -> Dict[str, str]:
        """Zwraca słownik wersji Cinema 4D"""
        return self.c4d_versions

    def set_c4d_versions(self, versions: Dict[str, str]):
        """Ustawia słownik wersji Cinema 4D"""
        self.c4d_versions = versions
        self.save_config()

    def get_logging_settings(self) -> tuple[bool, Optional[str]]:
        """Zwraca ustawienia logowania"""
        return self.log_to_file, self.log_file_path

    def set_logging_settings(
        self, log_to_file: bool, log_file_path: Optional[str] = None
    ):
        """Ustawia opcje logowania"""
        self.log_to_file = log_to_file
        self.log_file_path = log_file_path
        self.save_config()
