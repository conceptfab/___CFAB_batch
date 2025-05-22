import logging
import os
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

from core.config import Config
from models.task import RenderTask


class Cinema4DController:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.config = Config()
        self.c4d_installations = self.config.get_c4d_versions()

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
            c4d_exe = self.c4d_installations.get(task.cinema4d_version)
            if not c4d_exe:
                raise ValueError(
                    f"Nie znaleziono wersji Cinema 4D: {task.cinema4d_version}"
                )

            # Budowanie komendy CLI
            cmd = [c4d_exe, "-nogui", "-render", task.c4d_file_path]

            # Dodanie parametrów renderingu
            if task.start_frame is not None:
                cmd.extend(["-frame", f"{task.start_frame}"])
            if task.end_frame is not None:
                cmd.extend(["-frame", f"{task.start_frame}-{task.end_frame}"])

            if task.output_folder:
                cmd.extend(["-oimage", task.output_folder])

            # Wykonanie renderowania
            self.logger.info(f"Rozpoczynam renderowanie: {' '.join(cmd)}")

            process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )

            stdout, stderr = process.communicate()

            if process.returncode == 0:
                self.logger.info(f"Renderowanie zakończone pomyślnie: {task.name}")
                return True
            else:
                self.logger.error(f"Błąd renderowania: {stderr}")
                task.error_message = stderr
                return False

        except Exception as e:
            self.logger.error(f"Wyjątek podczas renderowania: {str(e)}")
            task.error_message = str(e)
            return False
