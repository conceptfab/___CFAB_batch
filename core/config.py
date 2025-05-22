import json
import os
from typing import Dict


class Config:
    def __init__(self):
        self.config_file = "config.json"
        self.c4d_versions: Dict[str, str] = {}
        self.load_config()

    def load_config(self):
        """Ładuje konfigurację z pliku"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.c4d_versions = data.get("c4d_versions", {})
            except Exception as e:
                print(f"Błąd ładowania konfiguracji: {str(e)}")
                self.c4d_versions = {}

    def save_config(self):
        """Zapisuje konfigurację do pliku"""
        try:
            data = {"c4d_versions": self.c4d_versions}
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
