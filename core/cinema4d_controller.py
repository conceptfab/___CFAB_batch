import logging
import os
import subprocess
import time
from pathlib import Path
from typing import Callable, Dict, List, Optional

from core.config import Config
from models.task import RenderTask
from utils.logger import setup_logger


class Cinema4DController:
    def __init__(self):
        self.logger = setup_logger("cinema4d_controller")
        self.config = Config()
        self.c4d_installations = self.config.get_c4d_versions()
        self.on_log_message: Optional[Callable[[str], None]] = None

    def validate_cinema4d_path(self, version: str) -> List[str]:
        """Weryfikuje czy ścieżka do Cinema 4D jest poprawna"""
        issues = []

        # Odśwież ścieżki przed użyciem
        self.c4d_installations = self.config.get_c4d_versions()

        c4d_exe = self.c4d_installations.get(version)
        if not c4d_exe:
            issues.append(f"Nie znaleziono wersji Cinema 4D: {version}")
            return issues

        if not os.path.exists(c4d_exe):
            issues.append(f"Plik Cinema 4D nie istnieje: {c4d_exe}")
            return issues

        if not os.access(c4d_exe, os.X_OK):
            issues.append(f"Brak uprawnień do uruchomienia Cinema 4D: {c4d_exe}")
            return issues

        return issues

    def validate_project(self, task: RenderTask) -> List[str]:
        """Weryfikuje projekt pod kątem brakujących tekstur i pluginów"""
        issues = []

        if not os.path.exists(task.c4d_file_path):
            issues.append(f"Plik projektu nie istnieje: {task.c4d_file_path}")
            return issues

        # Tutaj można dodać bardziej zaawansowaną walidację
        # np. parsowanie pliku C4D w poszukiwaniu referencji do tekstur

        return issues

    def render_task(self, task: RenderTask) -> bool:
        """Wykonuje renderowanie zadania"""
        try:
            # Walidacja ścieżki Cinema 4D
            issues = self.validate_cinema4d_path(task.cinema4d_version)
            if issues:
                task.error_message = "\n".join(issues)
                self.logger.error(f"Błędy walidacji: {task.error_message}")
                return False

            c4d_exe = self.c4d_installations.get(task.cinema4d_version)
            if not c4d_exe:
                raise ValueError(
                    f"Nie znaleziono wersji Cinema 4D: {task.cinema4d_version}"
                )

            # Zamień Cinema 4D.exe na Commandline.exe
            c4d_exe = c4d_exe.replace("Cinema 4D.exe", "Commandline.exe")
            self.logger.info(f"Używam Cinema 4D z: {c4d_exe}")

            # Budowanie komendy CLI zgodnie z dokumentacją
            cmd = [c4d_exe, "-render", task.c4d_file_path, "-verbose", "-console"]

            # Dodanie parametrów renderingu
            if task.start_frame is not None and task.end_frame is not None:
                cmd.extend(["-frame", f"{task.start_frame}-{task.end_frame}"])
                self.logger.info(
                    f"Renderowanie klatek: {task.start_frame}-{task.end_frame}"
                )
            elif task.start_frame is not None:
                cmd.extend(["-frame", f"{task.start_frame}"])
                self.logger.info(f"Renderowanie klatki: {task.start_frame}")

            if task.output_folder:
                cmd.extend(["-oimage", f'"{task.output_folder}"'])
                self.logger.info(f"Folder wyjściowy: {task.output_folder}")

            # Dodanie parametrów z render_settings
            if task.render_settings.get("threads"):
                cmd.extend(["-threads", str(task.render_settings["threads"])])
                self.logger.info(f"Liczba wątków: {task.render_settings['threads']}")

            if task.render_settings.get("shutdown"):
                cmd.append("-shutdown")
                self.logger.info("Włączono automatyczne wyłączenie po renderowaniu")

            if task.render_settings.get("quit"):
                cmd.append("-quit")
                self.logger.info("Włączono automatyczne zamknięcie po renderowaniu")

            # Wykonanie renderowania
            print(f"Rozpoczynam renderowanie: {' '.join(cmd)}")
            start_time = time.time()

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True,
            )

            # Czytanie wyjścia w czasie rzeczywistym
            while True:
                output = process.stdout.readline()
                if output == "" and process.poll() is not None:
                    break
                if output:
                    clean_output = output.strip()
                    if clean_output.startswith("Cinema 4D: "):
                        clean_output = clean_output[11:]  # Usuń prefix "Cinema 4D: "
                    print(clean_output)  # Wyświetl w konsoli
                    # Przekaż log do głównego okna
                    if self.on_log_message:
                        self.on_log_message(clean_output)

            # Pobierz pozostałe wyjście
            stdout, stderr = process.communicate()
            if stdout:
                for line in stdout.splitlines():
                    clean_line = line.strip()
                    if clean_line.startswith("Cinema 4D: "):
                        clean_line = clean_line[11:]
                    print(clean_line)
                    if self.on_log_message:
                        self.on_log_message(clean_line)

            # Logowanie błędów
            if stderr:
                for line in stderr.splitlines():
                    print(f"BŁĄD: {line.strip()}")
                    if self.on_log_message:
                        self.on_log_message(f"BŁĄD: {line.strip()}")

            end_time = time.time()
            duration = end_time - start_time
            print(f"Czas renderowania: {duration:.2f} sekund")

            if process.returncode == 0:
                print(f"Renderowanie zakończone pomyślnie: {task.name}")
                return True
            else:
                error_msg = f"Błąd renderowania (kod {process.returncode}): {stderr}"
                print(error_msg)
                task.error_message = error_msg
                return False

        except Exception as e:
            error_msg = f"Wyjątek podczas renderowania: {str(e)}"
            print(error_msg)
            task.error_message = error_msg
            return False
