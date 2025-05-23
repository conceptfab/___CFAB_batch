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
        self.config = Config()
        self.c4d_installations = self.config.get_c4d_versions()
        self.on_log_message: Optional[Callable[[str], None]] = None

        # Inicjalizacja loggera
        log_to_file, log_file_path = self.config.get_logging_settings()
        self.logger = setup_logger("cinema4d_controller", log_to_file, log_file_path)

    def reload_config(self):
        """Przeładowuje konfigurację i aktualizuje logger"""
        log_to_file, log_file_path = self.config.get_logging_settings()
        self.logger = setup_logger("cinema4d_controller", log_to_file, log_file_path)

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

            # Wykonanie renderowania
            cmd = [c4d_exe, "-render", task.c4d_file_path]

            # Dodaj parametry z render_settings TYLKO jeśli zostały wybrane w UI
            if (
                task.render_settings.get("threads")
                and task.render_settings["threads"] > 0
            ):
                cmd.extend(["-threads", str(task.render_settings["threads"])])
            if (
                task.render_settings.get("shutdown")
                and task.render_settings["shutdown"]
            ):
                cmd.append("-shutdown")
            if task.render_settings.get("quit") and task.render_settings["quit"]:
                cmd.append("-quit")
            if task.render_settings.get("use_gpu") and task.render_settings["use_gpu"]:
                cmd.append("-gpu")
            if task.render_settings.get("no_gui") and task.render_settings["no_gui"]:
                cmd.append("cmd-nogui")
            if (
                task.render_settings.get("debug_mode")
                and task.render_settings["debug_mode"]
            ):
                cmd.append("cmd-debug")
            if (
                task.render_settings.get("show_console")
                and task.render_settings["show_console"]
            ):
                cmd.append("-console")
            if (
                task.render_settings.get("log_file")
                and task.render_settings["log_file"]
            ):
                cmd.extend(["-log", task.render_settings["log_file"]])
            if task.render_settings.get("verbose") and task.render_settings["verbose"]:
                cmd.append("-verbose")
            if (
                task.render_settings.get("memory_limit")
                and task.render_settings["memory_limit"] > 0
            ):
                cmd.extend(["cmd-memory", str(task.render_settings["memory_limit"])])
            if (
                task.render_settings.get("priority")
                and task.render_settings["priority"]
            ):
                cmd.extend(["-priority", task.render_settings["priority"]])

            # Dodaj wymagane parametry na końcu
            cmd.extend(["-verbose", "-console"])

            # Logowanie komendy
            self.logger.info("=" * 80)
            self.logger.info("KOMENDA RENDEROWANIA:")
            self.logger.info(" ".join(cmd))
            self.logger.info("=" * 80)
            start_time = time.time()

            try:
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1,
                    universal_newlines=True,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )

                # Czytanie wyjścia w czasie rzeczywistym z timeoutem
                while True:
                    try:
                        output = process.stdout.readline()
                        if output == "" and process.poll() is not None:
                            break
                        if output:
                            clean_output = output.strip()
                            if clean_output.startswith("Cinema 4D: "):
                                clean_output = clean_output[11:]
                            self.logger.info(clean_output)
                            if self.on_log_message:
                                self.on_log_message(clean_output)
                    except Exception as e:
                        self.logger.error(f"Błąd podczas czytania wyjścia: {str(e)}")
                        break

                # Czekaj na zakończenie procesu z timeoutem
                try:
                    process.wait(timeout=300)  # 5 minut timeout
                except subprocess.TimeoutExpired:
                    self.logger.error("Timeout - proces przekroczył 5 minut")
                    process.kill()
                    task.error_message = "Timeout - proces przekroczył 5 minut"
                    return False

                # Pobierz pozostałe wyjście
                stdout, stderr = process.communicate()
                if stdout:
                    for line in stdout.splitlines():
                        clean_line = line.strip()
                        if clean_line.startswith("Cinema 4D: "):
                            clean_line = clean_line[11:]
                        self.logger.info(clean_line)
                        if self.on_log_message:
                            self.on_log_message(clean_line)

                # Logowanie błędów
                if stderr:
                    for line in stderr.splitlines():
                        error_msg = f"BŁĄD: {line.strip()}"
                        self.logger.error(error_msg)
                        if self.on_log_message:
                            self.on_log_message(error_msg)

                end_time = time.time()
                duration = end_time - start_time
                self.logger.info(f"Czas renderowania: {duration:.2f} sekund")

                if process.returncode == 0:
                    self.logger.info(f"Renderowanie zakończone pomyślnie: {task.name}")
                    return True
                else:
                    error_msg = (
                        f"Błąd renderowania (kod {process.returncode}): {stderr}"
                    )
                    self.logger.error(error_msg)
                    task.error_message = error_msg
                    return False

            except Exception as e:
                error_msg = f"Wyjątek podczas renderowania: {str(e)}"
                self.logger.error(error_msg)
                task.error_message = error_msg
                return False

        except Exception as e:
            error_msg = f"Wyjątek podczas renderowania: {str(e)}"
            self.logger.error(error_msg)
            task.error_message = error_msg
            return False
