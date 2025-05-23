import json
import os
import threading
import time
from datetime import datetime
from queue import Queue
from typing import Callable, List, Optional

from core.cinema4d_controller import Cinema4DController
from models.task import RenderTask, TaskStatus
from utils.logger import setup_logger


class QueueManager:
    TASKS_DIR = "tasks"

    def __init__(self):
        self.task_queue = Queue()
        self.tasks: List[RenderTask] = []
        self.current_task: Optional[RenderTask] = None
        self.is_processing = False
        self.worker_thread: Optional[threading.Thread] = None
        self.c4d_controller = Cinema4DController()
        self.logger = setup_logger("queue_manager")
        self.c4d_paths = self._load_c4d_paths()

        # Callbacks
        self.on_task_started: Optional[Callable[[RenderTask], None]] = None
        self.on_task_completed: Optional[Callable[[RenderTask], None]] = None
        self.on_task_failed: Optional[Callable[[RenderTask], None]] = None

        # Upewnij się, że folder tasks istnieje
        os.makedirs(self.TASKS_DIR, exist_ok=True)
        self.load_tasks()

    def _load_c4d_paths(self) -> dict:
        """Wczytuje ścieżki do Cinema 4D z config.json"""
        try:
            with open("config.json", "r", encoding="utf-8") as f:
                config = json.load(f)
                return config.get("c4d_versions", {})
        except Exception as e:
            self.logger.error(f"Błąd wczytywania config.json: {e}")
            return {}

    def add_task(self, task: RenderTask):
        """Dodaje zadanie do kolejki"""
        self.tasks.append(task)
        self.task_queue.put(task)
        self.logger.info(f"Dodano zadanie do kolejki: {task.name}")
        self.save_tasks()

    def remove_task(self, task_id: str) -> bool:
        """Usuwa zadanie z kolejki"""
        for task in self.tasks:
            if task.id == task_id and task.status == TaskStatus.PENDING:
                self.tasks.remove(task)
                task.status = TaskStatus.CANCELLED
                self.save_tasks()
                return True
        return False

    def edit_task(self, task_id: str, new_task: RenderTask) -> bool:
        """Edytuje istniejące zadanie (tylko PENDING)"""
        for i, task in enumerate(self.tasks):
            if task.id == task_id and task.status == TaskStatus.PENDING:
                self.tasks[i] = new_task
                self.save_tasks()
                return True
        return False

    def start_processing(self):
        """Rozpoczyna przetwarzanie kolejki"""
        if not self.is_processing:
            self.is_processing = True
            self.worker_thread = threading.Thread(target=self._process_queue)
            self.worker_thread.daemon = True
            self.worker_thread.start()
            self.logger.info("Rozpoczęto przetwarzanie kolejki")

    def stop_processing(self):
        """Zatrzymuje przetwarzanie kolejki"""
        self.is_processing = False
        if self.worker_thread:
            self.worker_thread.join()
        self.logger.info("Zatrzymano przetwarzanie kolejki")

    def _process_queue(self):
        """Główna pętla przetwarzania kolejki"""
        while self.is_processing:
            try:
                if not self.task_queue.empty():
                    task = self.task_queue.get(timeout=1)

                    if task.status == TaskStatus.CANCELLED:
                        continue

                    self._process_task(task)
                else:
                    time.sleep(0.1)
            except Exception as e:
                self.logger.error(f"Błąd w pętli przetwarzania: {str(e)}")

    def _process_task(self, task: RenderTask):
        """Przetwarza pojedyncze zadanie"""
        self.current_task = task
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()

        if self.on_task_started:
            self.on_task_started(task)

        self.logger.info(f"Rozpoczynam przetwarzanie zadania: {task.name}")

        # Walidacja projektu
        issues = self.c4d_controller.validate_project(task)
        if issues:
            task.status = TaskStatus.FAILED
            task.error_message = "; ".join(issues)
            task.completed_at = datetime.now()

            if self.on_task_failed:
                self.on_task_failed(task)
            return

        # Renderowanie
        success = self.c4d_controller.render_task(task)

        task.completed_at = datetime.now()

        if success:
            task.status = TaskStatus.COMPLETED
            if self.on_task_completed:
                self.on_task_completed(task)
        else:
            task.status = TaskStatus.FAILED
            if self.on_task_failed:
                self.on_task_failed(task)

        self.current_task = None

    def get_tasks(self) -> List[RenderTask]:
        """Zwraca listę wszystkich zadań"""
        return self.tasks

    def get_worker_status(self) -> List[dict]:
        """Zwraca status workerów"""
        # Na razie zwracamy tylko jeden worker (główny wątek)
        worker_status = {
            "worker_id": 1,
            "is_busy": self.current_task is not None,
            "current_task": self.current_task,
        }
        return [worker_status]

    def get_task_file_path(self, task: RenderTask) -> str:
        """Zwraca ścieżkę do pliku zadania"""
        timestamp = task.created_at.strftime("%Y%m%d_%H%M%S")
        return os.path.join(self.TASKS_DIR, f"task_{timestamp}_{task.id}.json")

    def save_tasks(self):
        """Zapisuje zadania do plików JSON"""
        try:
            # Zapisz każde zadanie do osobnego pliku
            for task in self.tasks:
                task_file = self.get_task_file_path(task)
                with open(task_file, "w", encoding="utf-8") as f:
                    json.dump(
                        self._task_to_dict(task),
                        f,
                        ensure_ascii=False,
                        indent=2,
                    )
        except Exception as e:
            self.logger.error(f"Błąd zapisu zadań: {e}")

    def load_tasks(self):
        """Wczytuje zadania z plików JSON"""
        try:
            # Upewnij się, że folder tasks istnieje
            os.makedirs(self.TASKS_DIR, exist_ok=True)

            # Wczytaj wszystkie pliki zadań z folderu tasks
            self.tasks = []
            for filename in os.listdir(self.TASKS_DIR):
                if filename.startswith("task_") and filename.endswith(".json"):
                    task_file = os.path.join(self.TASKS_DIR, filename)
                    with open(task_file, "r", encoding="utf-8") as f:
                        task_data = json.load(f)
                        self.tasks.append(self._dict_to_task(task_data))
        except Exception as e:
            self.logger.error(f"Błąd odczytu zadań: {e}")

    def _task_to_dict(self, task: RenderTask) -> dict:
        """Konwertuje zadanie do słownika"""
        d = task.__dict__.copy()
        d["status"] = task.status.value
        if task.created_at:
            d["created_at"] = task.created_at.isoformat()
        if task.started_at:
            d["started_at"] = task.started_at.isoformat()
        if task.completed_at:
            d["completed_at"] = task.completed_at.isoformat()

        # Odśwież ścieżki przed użyciem
        self.c4d_paths = self._load_c4d_paths()

        # Uproszczone polecenie - tylko podstawowe parametry
        c4d_path = self.c4d_paths.get(task.cinema4d_version)
        if not c4d_path:
            raise ValueError(
                f"Nie znaleziono ścieżki do Cinema 4D {task.cinema4d_version}"
            )

        # Zamień ukośniki w prawo na ukośniki w lewo w ścieżce do pliku C4D
        c4d_file_path = task.c4d_file_path.replace("/", "\\")

        # Rzeczywiste polecenie (bez escape'owania dla JSON)
        actual_command = f'"{c4d_path}" -render "{c4d_file_path}" -verbose -console'

        # Zapisz polecenie w formacie JSON (z escape'owaniem)
        d["command"] = actual_command.replace("\\", "\\\\").replace('"', '\\"')
        return d

    def _dict_to_task(self, d: dict) -> RenderTask:
        d = d.copy()
        # Usuń pole command, którego nie ma w klasie RenderTask
        d.pop("command", None)

        # Konwertuj status z stringa na enum
        if isinstance(d["status"], str):
            d["status"] = TaskStatus(d["status"])
        from datetime import datetime

        for field in ["created_at", "started_at", "completed_at"]:
            if d.get(field):
                d[field] = datetime.fromisoformat(d[field])
            else:
                d[field] = None
        return RenderTask(**d)
