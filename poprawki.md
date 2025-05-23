Analiza kodu i proponowane ulepszenia
Po przeanalizowaniu kodu aplikacji Cinema 4D Batch Renderer, identyfikuję kilka obszarów wymagających poprawy oraz możliwości wprowadzenia obsługi wielowątkowości.
🔧 Krytyczne poprawki
Plik: core/queue_manager.py
Problem: Brak importu datetime
python# Dodaj na początku pliku
from datetime import datetime
Plik: gui/main_window.py
Problem: Błąd w sprawdzaniu wyniku dialogu
python# W funkcji add_task() zmień:
if dialog.exec() == dialog.accepted:  # ← Poprawne
    task = dialog.get_task()
    self.queue_manager.add_task(task)
    self.update_tasks_table()
Plik: utils/resource_monitor.py
Problem: Błędna ścieżka dysku dla Windows
pythondef get_system_resources(self) -> Dict[str, float]:
    """Zwraca aktualny stan zasobów systemowych"""
    try:
        # Użyj głównego dysku systemowego
        import os
        disk_path = os.path.abspath(os.sep)  # '/' na Linux, 'C:\' na Windows
        
        return {
            "cpu": psutil.cpu_percent(interval=1),
            "memory": psutil.virtual_memory().percent,
            "disk": psutil.disk_usage(disk_path).percent,
        }
    except Exception as e:
        self.logger.error(f"Błąd odczytu zasobów systemowych: {str(e)}")
        return {"cpu": 0, "memory": 0, "disk": 0}
🚀 Wielowątkowość i współbieżność
1. Nowy plik: core/thread_manager.py
pythonimport threading
import concurrent.futures
import queue
from typing import List, Optional, Callable
from dataclasses import dataclass
from models.task import RenderTask, TaskStatus
from core.cinema4d_controller import Cinema4DController
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
            self.logger.info(f"Uruchomiono menedżer wątków z {self.max_workers} workerami")

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
        self.logger.info(f"Dodano zadanie do kolejki: {task.name} (priorytet: {priority})")

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
                            self._execute_task, 
                            task, 
                            available_worker.worker_id
                        )
                        
                        # Dodaj callback dla zakończenia zadania
                        future.add_done_callback(
                            lambda f, worker=available_worker: self._task_completed(f, worker)
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
2. Zaktualizowany plik: core/queue_manager.py
pythonimport threading
import time
from datetime import datetime
from typing import Callable, List, Optional

from core.thread_manager import ThreadManager
from models.task import RenderTask, TaskStatus
from utils.logger import setup_logger


class QueueManager:
    def __init__(self, max_workers: int = None):
        self.tasks: List[RenderTask] = []
        self.thread_manager = ThreadManager(max_workers)
        self.logger = setup_logger("queue_manager")
        self._lock = threading.Lock()  # Ochrona przed dostępem wielowątkowym

        # Callbacks
        self.on_task_started: Optional[Callable[[RenderTask], None]] = None
        self.on_task_completed: Optional[Callable[[RenderTask], None]] = None
        self.on_task_failed: Optional[Callable[[RenderTask], None]] = None
        self.on_queue_status_changed: Optional[Callable[[], None]] = None

        # Konfiguracja callbacków thread managera
        self.thread_manager.on_task_started = self._on_task_started
        self.thread_manager.on_task_completed = self._on_task_completed
        self.thread_manager.on_task_failed = self._on_task_failed

    def add_task(self, task: RenderTask, priority: int = 1):
        """Dodaje zadanie do kolejki"""
        with self._lock:
            self.tasks.append(task)
        
        self.thread_manager.add_task(task, priority)
        self.logger.info(f"Dodano zadanie do kolejki: {task.name}")
        
        if self.on_queue_status_changed:
            self.on_queue_status_changed()

    def remove_task(self, task_id: str) -> bool:
        """Usuwa zadanie z kolejki (tylko jeśli status = PENDING)"""
        with self._lock:
            for task in self.tasks:
                if task.id == task_id and task.status == TaskStatus.PENDING:
                    task.status = TaskStatus.CANCELLED
                    if self.on_queue_status_changed:
                        self.on_queue_status_changed()
                    return True
        return False

    def start_processing(self):
        """Rozpoczyna przetwarzanie kolejki"""
        self.thread_manager.start()
        self.logger.info("Rozpoczęto przetwarzanie kolejki")

    def stop_processing(self):
        """Zatrzymuje przetwarzanie kolejki"""
        self.thread_manager.stop()
        self.logger.info("Zatrzymano przetwarzanie kolejki")

    def get_tasks(self) -> List[RenderTask]:
        """Zwraca kopię listy zadań (thread-safe)"""
        with self._lock:
            return self.tasks.copy()

    def get_worker_status(self):
        """Zwraca status workerów"""
        return self.thread_manager.get_worker_status()

    def _on_task_started(self, task: RenderTask, worker_id: int):
        """Callback z thread managera - zadanie rozpoczęte"""
        self.logger.info(f"Worker {worker_id}: Rozpoczęto zadanie {task.name}")
        if self.on_task_started:
            self.on_task_started(task)
        if self.on_queue_status_changed:
            self.on_queue_status_changed()

    def _on_task_completed(self, task: RenderTask, worker_id: int):
        """Callback z thread managera - zadanie zakończone"""
        self.logger.info(f"Worker {worker_id}: Zakończono zadanie {task.name}")
        if self.on_task_completed:
            self.on_task_completed(task)
        if self.on_queue_status_changed:
            self.on_queue_status_changed()

    def _on_task_failed(self, task: RenderTask, worker_id: int):
        """Callback z thread managera - zadanie nieudane"""
        self.logger.error(f"Worker {worker_id}: Błąd zadania {task.name}: {task.error_message}")
        if self.on_task_failed:
            self.on_task_failed(task)
        if self.on_queue_status_changed:
            self.on_queue_status_changed()
🎨 Ulepszenia GUI
Plik: gui/worker_status_widget.py
pythonfrom PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from core.thread_manager import RenderWorker


class WorkerStatusWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.workers = []
        self.init_ui()

    def init_ui(self):
        """Inicjalizuje interfejs widżetu statusu workerów"""
        layout = QVBoxLayout(self)
        
        self.workers_group = QGroupBox("Status workerów")
        self.workers_group.setStyleSheet(
            """
            QGroupBox {
                background-color: #252526;
                border: 1px solid #3F3F46;
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 16px;
            }
            QGroupBox::title {
                color: #CCCCCC;
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px;
            }
        """
        )
        
        self.workers_layout = QVBoxLayout(self.workers_group)
        layout.addWidget(self.workers_group)

    def update_workers(self, workers: list[RenderWorker]):
        """Aktualizuje wyświetlanie statusu workerów"""
        # Usuń stare widżety
        for i in reversed(range(self.workers_layout.count())):
            child = self.workers_layout.itemAt(i).widget()
            if child:
                child.setParent(None)

        # Dodaj nowe widżety dla każdego workera
        for worker in workers:
            worker_widget = QWidget()
            worker_layout = QHBoxLayout(worker_widget)
            
            # Etykieta workera
            worker_label = QLabel(f"Worker {worker.worker_id}:")
            worker_layout.addWidget(worker_label)
            
            # Status
            if worker.is_busy and worker.current_task:
                status_label = QLabel(f"Renderuje: {worker.current_task.name}")
                status_label.setStyleSheet("color: #10B981;")  # Zielony
            else:
                status_label = QLabel("Bezczynny")
                status_label.setStyleSheet("color: #9CA3AF;")  # Szary
            
            worker_layout.addWidget(status_label)
            worker_layout.addStretch()
            
            self.workers_layout.addWidget(worker_widget)
Zaktualizowany plik: gui/main_window.py
python# Dodaj import na początku
from gui.worker_status_widget import WorkerStatusWidget

# W metodzie init_ui(), po sekcji zasobów systemowych dodaj:
# Status workerów
self.worker_status_widget = WorkerStatusWidget()
info_layout.addWidget(self.worker_status_widget)

# W metodzie update_ui() dodaj:
# Aktualizacja statusu workerów
workers = self.queue_manager.get_worker_status()
self.worker_status_widget.update_workers(workers)
📁 Nowe funkcjonalności
Plik: utils/file_monitor.py
pythonimport os
import time
from pathlib import Path
from typing import List, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

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
            if file_path.suffix.lower() in ['.png', '.jpg', '.jpeg', '.exr', '.tiff', '.tga']:
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
Aktualizacja requirements.txt
PyQt6>=6.4.0
psutil>=5.9.0
watchdog>=3.0.0
Pillow>=9.0.0