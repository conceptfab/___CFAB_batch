import concurrent.futures
import queue
import threading
from dataclasses import dataclass
from typing import Callable, List, Optional

from core.cinema4d_controller import Cinema4DController
from models.task import RenderTask, TaskStatus
from utils.logger import setup_logger
from utils.resource_monitor import ResourceMonitor


@dataclass
class RenderWorker:
    """Worker do obsługi pojedynczego zadania renderingu"""

    worker_id: int
    is_busy: bool = False
    current_task: Optional[RenderTask] = None


class ThreadManager:
    def __init__(self, max_workers: int = None):
        self.logger = setup_logger("thread_manager")
        self.resource_monitor = ResourceMonitor()
        self.c4d_controller = Cinema4DController()

        # Automatyczne określenie liczby workerów na podstawie zasobów
        if max_workers is None:
            max_workers = self.resource_monitor.get_optimal_thread_count()

        self.max_workers = max_workers
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
        self.task_queue = queue.PriorityQueue()
        self.workers: List[RenderWorker] = [
            RenderWorker(worker_id=i) for i in range(max_workers)
        ]

        self.is_running = False
        self.dispatcher_thread: Optional[threading.Thread] = None

        # Callbacks
        self.on_task_started: Optional[Callable[[RenderTask, int], None]] = None
        self.on_task_completed: Optional[Callable[[RenderTask, int], None]] = None
        self.on_task_failed: Optional[Callable[[RenderTask, int], None]] = None
        self.on_worker_status_changed: Optional[Callable[[RenderWorker], None]] = None

    def start(self):
        """Rozpoczyna menedżer wątków"""
        if not self.is_running:
            self.is_running = True
            self.dispatcher_thread = threading.Thread(target=self._dispatch_tasks)
            self.dispatcher_thread.daemon = True
            self.dispatcher_thread.start()
            self.logger.info(
                f"Uruchomiono menedżer wątków z {self.max_workers} workerami"
            )

    def stop(self):
        """Zatrzymuje menedżer wątków"""
        self.is_running = False
        if self.dispatcher_thread:
            self.dispatcher_thread.join()
        self.executor.shutdown(wait=True)
        self.logger.info("Zatrzymano menedżer wątków")

    def add_task(self, task: RenderTask, priority: int = 1):
        """Dodaje zadanie do kolejki z priorytetem (niższy = wyższy priorytet)"""
        self.task_queue.put((priority, task))
        self.logger.info(
            f"Dodano zadanie do kolejki: {task.name} (priorytet: {priority})"
        )

    def _dispatch_tasks(self):
        """Główna pętla dyspozytora zadań"""
        while self.is_running:
            try:
                # Sprawdź czy są dostępni workerzy i czy zasoby pozwalają na renderowanie
                available_worker = self._get_available_worker()
                if available_worker and self.resource_monitor.should_start_render():
                    try:
                        # Pobierz zadanie z kolejki (timeout 1 sekunda)
                        priority, task = self.task_queue.get(timeout=1.0)

                        # Przypisz zadanie do workera
                        available_worker.is_busy = True
                        available_worker.current_task = task

                        if self.on_worker_status_changed:
                            self.on_worker_status_changed(available_worker)

                        # Uruchom zadanie w osobnym wątku
                        future = self.executor.submit(
                            self._execute_task, task, available_worker.worker_id
                        )

                        # Dodaj callback dla zakończenia zadania
                        future.add_done_callback(
                            lambda f, worker=available_worker: self._task_completed(
                                f, worker
                            )
                        )

                    except queue.Empty:
                        continue
                else:
                    # Brak dostępnych workerów lub zasobów, czekaj
                    threading.Event().wait(0.5)

            except Exception as e:
                self.logger.error(f"Błąd w dyspozytorze zadań: {str(e)}")

    def _get_available_worker(self) -> Optional[RenderWorker]:
        """Zwraca pierwszego dostępnego workera"""
        for worker in self.workers:
            if not worker.is_busy:
                return worker
        return None

    def _execute_task(self, task: RenderTask, worker_id: int) -> bool:
        """Wykonuje zadanie renderingu"""
        from datetime import datetime

        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()

        if self.on_task_started:
            self.on_task_started(task, worker_id)

        self.logger.info(f"Worker {worker_id}: Rozpoczynam zadanie {task.name}")

        try:
            # Walidacja projektu
            issues = self.c4d_controller.validate_project(task)
            if issues:
                task.status = TaskStatus.FAILED
                task.error_message = "; ".join(issues)
                return False

            # Renderowanie
            success = self.c4d_controller.render_task(task)

            if success:
                task.status = TaskStatus.COMPLETED
                return True
            else:
                task.status = TaskStatus.FAILED
                return False

        except Exception as e:
            self.logger.error(f"Worker {worker_id}: Błąd zadania {task.name}: {str(e)}")
            task.status = TaskStatus.FAILED
            task.error_message = str(e)
            return False
        finally:
            task.completed_at = datetime.now()

    def _task_completed(self, future: concurrent.futures.Future, worker: RenderWorker):
        """Callback wywoływany po zakończeniu zadania"""
        task = worker.current_task
        success = False

        try:
            success = future.result()
        except Exception as e:
            self.logger.error(f"Błąd w zadaniu {task.name}: {str(e)}")
            task.error_message = str(e)
            task.status = TaskStatus.FAILED

        # Zwolnij workera
        worker.is_busy = False
        worker.current_task = None

        if self.on_worker_status_changed:
            self.on_worker_status_changed(worker)

        # Wywołaj odpowiedni callback
        if success and self.on_task_completed:
            self.on_task_completed(task, worker.worker_id)
        elif not success and self.on_task_failed:
            self.on_task_failed(task, worker.worker_id)

    def get_worker_status(self) -> List[RenderWorker]:
        """Zwraca status wszystkich workerów"""
        return self.workers.copy()

    def cancel_task(self, task_id: str) -> bool:
        """Anuluje zadanie (jeśli jeszcze nie zostało rozpoczęte)"""
        # Trudne do implementacji w ThreadPoolExecutor
        # Można rozważyć zmianę na własną implementację
        self.logger.warning("Anulowanie zadań nie jest obecnie obsługiwane")
        return False
