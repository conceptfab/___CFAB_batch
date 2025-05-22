import threading
import time
from datetime import datetime
from queue import Queue
from typing import Callable, List, Optional

from core.cinema4d_controller import Cinema4DController
from models.task import RenderTask, TaskStatus
from utils.logger import setup_logger


class QueueManager:
    def __init__(self):
        self.task_queue = Queue()
        self.tasks: List[RenderTask] = []
        self.current_task: Optional[RenderTask] = None
        self.is_processing = False
        self.worker_thread: Optional[threading.Thread] = None
        self.c4d_controller = Cinema4DController()
        self.logger = setup_logger("queue_manager")

        # Callbacks
        self.on_task_started: Optional[Callable[[RenderTask], None]] = None
        self.on_task_completed: Optional[Callable[[RenderTask], None]] = None
        self.on_task_failed: Optional[Callable[[RenderTask], None]] = None

    def add_task(self, task: RenderTask):
        """Dodaje zadanie do kolejki"""
        self.tasks.append(task)
        self.task_queue.put(task)
        self.logger.info(f"Dodano zadanie do kolejki: {task.name}")

    def remove_task(self, task_id: str) -> bool:
        """Usuwa zadanie z kolejki"""
        for task in self.tasks:
            if task.id == task_id and task.status == TaskStatus.PENDING:
                self.tasks.remove(task)
                # Trudno usunąć z Queue, więc oznaczamy jako anulowane
                task.status = TaskStatus.CANCELLED
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
