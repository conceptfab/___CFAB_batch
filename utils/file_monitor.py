import os
import time
from pathlib import Path
from typing import List, Optional

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from models.task import RenderTask
from utils.logger import setup_logger


class RenderOutputHandler(FileSystemEventHandler):
    """Handler monitorujący pliki wyjściowe renderingu"""

    def __init__(self, task: RenderTask, callback=None):
        self.task = task
        self.callback = callback
        self.logger = setup_logger("file_monitor")
        self.expected_files = set()
        self.found_files = set()

    def on_created(self, event):
        """Wywoływane gdy zostanie utworzony nowy plik"""
        if not event.is_directory:
            file_path = Path(event.src_path)

            # Sprawdź czy to plik renderingu (np. .png, .jpg, .exr)
            if file_path.suffix.lower() in [
                ".png",
                ".jpg",
                ".jpeg",
                ".exr",
                ".tiff",
                ".tga",
            ]:
                self.found_files.add(str(file_path))
                self.logger.info(f"Wykryto plik renderingu: {file_path}")

                if self.callback:
                    self.callback(str(file_path))


class FileMonitor:
    def __init__(self):
        self.observer = Observer()
        self.logger = setup_logger("file_monitor")
        self.active_monitors = {}

    def start_monitoring(self, task: RenderTask, callback=None):
        """Rozpoczyna monitorowanie folderu wyjściowego dla zadania"""
        if not os.path.exists(task.output_folder):
            os.makedirs(task.output_folder, exist_ok=True)

        handler = RenderOutputHandler(task, callback)
        self.observer.schedule(handler, task.output_folder, recursive=False)
        self.active_monitors[task.id] = handler

        if not self.observer.is_alive():
            self.observer.start()

        self.logger.info(f"Rozpoczęto monitorowanie folderu: {task.output_folder}")

    def stop_monitoring(self, task_id: str):
        """Zatrzymuje monitorowanie dla konkretnego zadania"""
        if task_id in self.active_monitors:
            del self.active_monitors[task_id]

    def stop_all(self):
        """Zatrzymuje całkowicie obserwator plików"""
        self.observer.stop()
        self.observer.join()
        self.active_monitors.clear()

    def get_found_files(self, task_id: str) -> List[str]:
        """Zwraca listę znalezionych plików dla zadania"""
        if task_id in self.active_monitors:
            return list(self.active_monitors[task_id].found_files)
        return []
