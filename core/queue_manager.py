import json
import os
import threading
import time
from datetime import datetime
from queue import Queue
from typing import Callable, List, Optional

from core.cinema4d_controller import Cinema4DController
from core.config import Config
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
        self.config = Config()
        self.c4d_paths = self._load_c4d_paths()

        # Inicjalizacja loggera
        log_to_file, log_file_path = self.config.get_logging_settings()
        self.logger = setup_logger("queue_manager", log_to_file, log_file_path)

        # Callbacks
        self.on_task_started: Optional[Callable[[RenderTask], None]] = None
        self.on_task_completed: Optional[Callable[[RenderTask], None]] = None
        self.on_task_failed: Optional[Callable[[RenderTask], None]] = None

        # Upewnij się, że folder tasks istnieje
        os.makedirs(self.TASKS_DIR, exist_ok=True)

        # Wczytaj zadania, ale nie dodawaj ich do kolejki
        self._load_tasks_from_files()

    def _load_c4d_paths(self) -> dict:
        """Wczytuje ścieżki do Cinema 4D z config.json"""
        try:
            with open("config.json", "r", encoding="utf-8") as f:
                config = json.load(f)
                return config.get("c4d_versions", {})
        except Exception as e:
            self.logger.error(f"Błąd wczytywania config.json: {e}")
            return {}

    def _load_tasks_from_files(self):
        """Wczytuje zadania z plików JSON bez dodawania do kolejki"""
        try:
            # Wczytaj wszystkie pliki zadań z folderu tasks
            self.tasks = []
            for filename in os.listdir(self.TASKS_DIR):
                if filename.startswith("task_") and filename.endswith(".json"):
                    task_file = os.path.join(self.TASKS_DIR, filename)
                    with open(task_file, "r", encoding="utf-8") as f:
                        task_data = json.load(f)
                        task = self._dict_to_task(task_data)
                        self.tasks.append(task)

            self.logger.info(f"Wczytano {len(self.tasks)} zadań")
        except Exception as e:
            self.logger.error(f"Błąd odczytu zadań: {e}")

    def load_tasks(self):
        """Wczytuje zadania i dodaje PENDING do kolejki"""
        self._load_tasks_from_files()

        # Wyczyść kolejkę
        while not self.task_queue.empty():
            self.task_queue.get()

        # Dodaj tylko PENDING zadania do kolejki
        pending_count = 0
        for task in self.tasks:
            if task.status == TaskStatus.PENDING:
                self.task_queue.put(task)
                pending_count += 1
                self.logger.info(f"Dodano zadanie do kolejki: {task.name}")

        self.logger.info(f"Dodano do kolejki {pending_count} zadań")
        self.save_tasks()

    def add_task(self, task: RenderTask):
        """Dodaje zadanie do kolejki"""
        self.logger.info(f"Dodawanie zadania: {task.name}")
        self.logger.info(f"Plik C4D: {task.c4d_file_path}")
        self.logger.info(f"Folder wyjściowy: {task.output_folder}")
        self.logger.info(f"Wersja C4D: {task.cinema4d_version}")

        self.tasks.append(task)
        self.task_queue.put(task)
        self.logger.info(f"Dodano zadanie do kolejki: {task.name}")
        self.logger.info(f"Aktualna liczba zadań w kolejce: {self.task_queue.qsize()}")
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
            # Przed rozpoczęciem, upewnij się że wszystkie PENDING zadania są w kolejce
            for task in self.tasks:
                if task.status == TaskStatus.PENDING and task not in list(
                    self.task_queue.queue
                ):
                    self.task_queue.put(task)
                    self.logger.info(f"Dodano zadanie do kolejki: {task.name}")

            self.is_processing = True
            self.worker_thread = threading.Thread(
                target=self._process_queue, daemon=True
            )
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
        self.logger.info("Uruchomiono wątek przetwarzania kolejki")
        self.logger.info(f"Liczba zadań w kolejce: {self.task_queue.qsize()}")
        self.logger.info(f"Liczba wszystkich zadań: {len(self.tasks)}")

        while self.is_processing:
            try:
                if not self.task_queue.empty():
                    task = self.task_queue.get(timeout=1)
                    self.logger.info(f"Pobrano zadanie z kolejki: {task.name}")
                    self.logger.info(f"Status zadania: {task.status}")
                    self.logger.info(
                        f"Pozostało zadań w kolejce: {self.task_queue.qsize()}"
                    )

                    if task.status == TaskStatus.CANCELLED:
                        self.logger.info(f"Pominięto anulowane zadanie: {task.name}")
                        continue

                    self._process_task(task)
                else:
                    time.sleep(0.1)
            except Exception as e:
                self.logger.error(f"Błąd w pętli przetwarzania: {str(e)}")
                time.sleep(1)  # Dodajemy opóźnienie przy błędzie

    def _process_task(self, task: RenderTask):
        """Przetwarza pojedyncze zadanie"""
        try:
            self.current_task = task
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now()

            if self.on_task_started:
                self.on_task_started(task)

            self.logger.info(f"Rozpoczynam przetwarzanie zadania: {task.name}")
            self.logger.info(f"Plik C4D: {task.c4d_file_path}")
            self.logger.info(f"Folder wyjściowy: {task.output_folder}")
            self.logger.info(f"Wersja C4D: {task.cinema4d_version}")

            # Walidacja projektu
            self.logger.info("Walidacja projektu...")
            issues = self.c4d_controller.validate_project(task)
            if issues:
                self.logger.error(f"Błędy walidacji: {issues}")
                task.status = TaskStatus.FAILED
                task.error_message = "; ".join(issues)
                task.completed_at = datetime.now()

                if self.on_task_failed:
                    self.on_task_failed(task)
                return

            # Renderowanie
            self.logger.info("Rozpoczynam renderowanie...")
            success = self.c4d_controller.render_task(task)

            task.completed_at = datetime.now()

            if success:
                self.logger.info(f"Zadanie zakończone sukcesem: {task.name}")
                task.status = TaskStatus.COMPLETED
                if self.on_task_completed:
                    self.on_task_completed(task)
            else:
                self.logger.error(f"Zadanie zakończone błędem: {task.name}")
                task.status = TaskStatus.FAILED
                if self.on_task_failed:
                    self.on_task_failed(task)

        except Exception as e:
            self.logger.error(f"Błąd podczas przetwarzania zadania: {str(e)}")
            task.status = TaskStatus.FAILED
            task.error_message = str(e)
            task.completed_at = datetime.now()
            if self.on_task_failed:
                self.on_task_failed(task)
        finally:
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

        # Debugowanie - wyświetl ustawienia
        print("Render settings w _task_to_dict:", task.render_settings)

        # Odśwież ścieżki przed użyciem
        self.c4d_paths = self._load_c4d_paths()

        # Pobierz ścieżkę do Cinema 4D
        c4d_path = self.c4d_paths.get(task.cinema4d_version)
        if not c4d_path:
            raise ValueError(
                f"Nie znaleziono ścieżki do Cinema 4D {task.cinema4d_version}"
            )

        # Zamień Cinema 4D.exe na Commandline.exe
        c4d_path = c4d_path.replace("Cinema 4D.exe", "Commandline.exe")

        # Zamień ukośniki w prawo na ukośniki w lewo w ścieżce do pliku C4D
        c4d_file_path = task.c4d_file_path.replace("/", "\\")

        # Buduj komendę
        cmd = [c4d_path, "-render", c4d_file_path, "-verbose", "-console"]

        # Debugowanie - wyświetl początkową komendę
        print("Początkowa komenda:", cmd)

        # Dodaj parametry z render_settings TYLKO jeśli zostały wybrane w UI
        if task.render_settings.get("threads") and task.render_settings["threads"] > 0:
            cmd.extend(["-threads", str(task.render_settings["threads"])])
        if task.render_settings.get("shutdown") and task.render_settings["shutdown"]:
            cmd.append("-shutdown")
        if task.render_settings.get("quit") and task.render_settings["quit"]:
            cmd.append("-quit")
        if task.render_settings.get("use_gpu") and task.render_settings["use_gpu"]:
            cmd.append("-gpu")
        if task.render_settings.get("no_gui") and task.render_settings["no_gui"]:
            cmd.append("cmd-nogui")
        if (
            task.render_settings.get("batch_mode")
            and task.render_settings["batch_mode"]
        ):
            cmd.append("-batch")
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
        if task.render_settings.get("log_file") and task.render_settings["log_file"]:
            cmd.append(f'-log "{task.render_settings["log_file"]}"')
        if task.render_settings.get("verbose") and task.render_settings["verbose"]:
            cmd.append("-verbose")
        if (
            task.render_settings.get("memory_limit")
            and task.render_settings["memory_limit"] > 0
        ):
            cmd.append(f"cmd-memory {task.render_settings['memory_limit']}")
        if task.render_settings.get("priority") and task.render_settings["priority"]:
            cmd.append(f"-priority {task.render_settings['priority']}")

        # Debugowanie - wyświetl końcową komendę
        print("Końcowa komenda:", cmd)

        # Zapisz komendę w formacie JSON
        d["command"] = " ".join(cmd)
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

    def reload_config(self):
        """Przeładowuje konfigurację i aktualizuje logger"""
        log_to_file, log_file_path = self.config.get_logging_settings()
        self.logger = setup_logger("queue_manager", log_to_file, log_file_path)
