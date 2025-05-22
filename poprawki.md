Analiza założeń i architektura rozwiązania
Główne komponenty systemu:

GUI (PyQt6) - interfejs użytkownika
Queue Manager - zarządzanie kolejką zadań
Cinema 4D Controller - komunikacja z C4D przez CLI
Task Manager - wykonywanie zadań
Logger - system logowania
File Monitor - monitorowanie plików
Resource Monitor - kontrola zasobów systemowych
Email Reporter - wysyłanie raportów

Struktura plików projektu
cinema4d_batch_renderer/
├── main.py
├── gui/
│   ├── __init__.py
│   ├── main_window.py
│   ├── task_dialog.py
│   └── widgets/
├── core/
│   ├── __init__.py
│   ├── queue_manager.py
│   ├── task_manager.py
│   ├── cinema4d_controller.py
│   └── config.py
├── utils/
│   ├── __init__.py
│   ├── logger.py
│   ├── file_monitor.py
│   ├── resource_monitor.py
│   └── email_reporter.py
├── models/
│   ├── __init__.py
│   └── task.py
└── resources/
    └── icons/
Zmiany w kodzie
Plik: main.py
Opis: Główny punkt wejścia aplikacji
pythonimport sys
from PyQt6.QtWidgets import QApplication
from gui.main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Cinema 4D Batch Renderer")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
Plik: models/task.py
Opis: Model danych dla zadania renderingu
pythonfrom dataclasses import dataclass, field
from typing import Optional, Dict, Any
from enum import Enum
from datetime import datetime

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class RenderTask:
    id: str
    name: str
    c4d_file_path: str
    output_folder: str
    cinema4d_version: str
    status: TaskStatus = TaskStatus.PENDING
    start_frame: Optional[int] = None
    end_frame: Optional[int] = None
    render_settings: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    output_files: list = field(default_factory=list)
    
    @property
    def duration(self) -> Optional[float]:
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
Plik: core/cinema4d_controller.py
Opis: Kontroler do komunikacji z Cinema 4D przez CLI
pythonimport subprocess
import os
import logging
from pathlib import Path
from typing import Optional, List, Dict
from models.task import RenderTask

class Cinema4DController:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.c4d_installations = self._discover_c4d_installations()
    
    def _discover_c4d_installations(self) -> Dict[str, str]:
        """Wykrywa zainstalowane wersje Cinema 4D"""
        installations = {}
        
        # Windows paths
        program_files = [
            "C:/Program Files/Maxon Cinema 4D",
            "C:/Program Files/MAXON/Cinema 4D"
        ]
        
        for base_path in program_files:
            if os.path.exists(base_path):
                for item in os.listdir(base_path):
                    version_path = os.path.join(base_path, item)
                    exe_path = os.path.join(version_path, "Cinema 4D.exe")
                    if os.path.exists(exe_path):
                        installations[item] = exe_path
        
        return installations
    
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
                raise ValueError(f"Nie znaleziono wersji Cinema 4D: {task.cinema4d_version}")
            
            # Budowanie komendy CLI
            cmd = [
                c4d_exe,
                "-nogui",
                "-render",
                task.c4d_file_path
            ]
            
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
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
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
Plik: core/queue_manager.py
Opis: Zarządca kolejki zadań renderingu
pythonimport threading
import time
from typing import List, Optional, Callable
from queue import Queue
from models.task import RenderTask, TaskStatus
from core.cinema4d_controller import Cinema4DController
from utils.logger import setup_logger
import logging

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
Plik: gui/main_window.py
Opis: Główne okno aplikacji
pythonfrom PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QTableWidget, QTableWidgetItem,
                             QProgressBar, QLabel, QTextEdit, QSplitter,
                             QGroupBox, QGridLayout)
from PyQt6.QtCore import QTimer, pyqtSignal
from PyQt6.QtGui import QIcon
from core.queue_manager import QueueManager
from gui.task_dialog import TaskDialog
from models.task import RenderTask, TaskStatus
from utils.resource_monitor import ResourceMonitor
import logging

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.queue_manager = QueueManager()
        self.resource_monitor = ResourceMonitor()
        self.init_ui()
        self.setup_connections()
        self.setup_timer()
        
    def init_ui(self):
        """Inicjalizuje interfejs użytkownika"""
        self.setWindowTitle("Cinema 4D Batch Renderer")
        self.setGeometry(100, 100, 1200, 800)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Główny layout
        main_layout = QVBoxLayout(central_widget)
        
        # Toolbar
        toolbar_layout = QHBoxLayout()
        self.add_task_btn = QPushButton("Dodaj zadanie")
        self.remove_task_btn = QPushButton("Usuń zadanie")
        self.start_queue_btn = QPushButton("Start kolejki")
        self.stop_queue_btn = QPushButton("Stop kolejki")
        
        toolbar_layout.addWidget(self.add_task_btn)
        toolbar_layout.addWidget(self.remove_task_btn)
        toolbar_layout.addWidget(self.start_queue_btn)
        toolbar_layout.addWidget(self.stop_queue_btn)
        toolbar_layout.addStretch()
        
        main_layout.addLayout(toolbar_layout)
        
        # Splitter dla głównego obszaru
        splitter = QSplitter()
        main_layout.addWidget(splitter)
        
        # Tabela zadań
        self.tasks_table = QTableWidget()
        self.tasks_table.setColumnCount(6)
        self.tasks_table.setHorizontalHeaderLabels([
            "Nazwa", "Status", "Plik C4D", "Folder wyjściowy", 
            "Wersja C4D", "Czas"
        ])
        splitter.addWidget(self.tasks_table)
        
        # Panel informacyjny
        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)
        
        # Zasoby systemowe
        resources_group = QGroupBox("Zasoby systemowe")
        resources_layout = QGridLayout(resources_group)
        
        self.cpu_label = QLabel("CPU: 0%")
        self.memory_label = QLabel("RAM: 0%")
        self.disk_label = QLabel("Dysk: 0%")
        
        resources_layout.addWidget(self.cpu_label, 0, 0)
        resources_layout.addWidget(self.memory_label, 0, 1)
        resources_layout.addWidget(self.disk_label, 1, 0)
        
        info_layout.addWidget(resources_group)
        
        # Logi
        logs_group = QGroupBox("Logi")
        logs_layout = QVBoxLayout(logs_group)
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(300)
        logs_layout.addWidget(self.log_text)
        info_layout.addWidget(logs_group)
        
        splitter.addWidget(info_widget)
        splitter.setSizes([800, 400])
        
        # Status bar
        self.statusBar().showMessage("Gotowy")
    
    def setup_connections(self):
        """Konfiguruje połączenia sygnałów"""
        self.add_task_btn.clicked.connect(self.add_task)
        self.remove_task_btn.clicked.connect(self.remove_task)
        self.start_queue_btn.clicked.connect(self.start_queue)
        self.stop_queue_btn.clicked.connect(self.stop_queue)
        
        # Callbacks dla queue managera
        self.queue_manager.on_task_started = self.on_task_started
        self.queue_manager.on_task_completed = self.on_task_completed
        self.queue_manager.on_task_failed = self.on_task_failed
    
    def setup_timer(self):
        """Konfiguruje timer dla aktualizacji UI"""
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_ui)
        self.update_timer.start(1000)  # Aktualizacja co sekundę
    
    def add_task(self):
        """Otwiera dialog dodawania zadania"""
        dialog = TaskDialog(self)
        if dialog.exec() == dialog.Accepted:
            task = dialog.get_task()
            self.queue_manager.add_task(task)
            self.update_tasks_table()
    
    def remove_task(self):
        """Usuwa wybrane zadanie"""
        current_row = self.tasks_table.currentRow()
        if current_row >= 0:
            task = self.queue_manager.tasks[current_row]
            if self.queue_manager.remove_task(task.id):
                self.update_tasks_table()
    
    def start_queue(self):
        """Rozpoczyna przetwarzanie kolejki"""
        self.queue_manager.start_processing()
        self.start_queue_btn.setEnabled(False)
        self.stop_queue_btn.setEnabled(True)
        self.statusBar().showMessage("Przetwarzanie kolejki...")
    
    def stop_queue(self):
        """Zatrzymuje przetwarzanie kolejki"""
        self.queue_manager.stop_processing()
        self.start_queue_btn.setEnabled(True)
        self.stop_queue_btn.setEnabled(False)
        self.statusBar().showMessage("Kolejka zatrzymana")
    
    def update_tasks_table(self):
        """Aktualizuje tabelę zadań"""
        self.tasks_table.setRowCount(len(self.queue_manager.tasks))
        
        for row, task in enumerate(self.queue_manager.tasks):
            self.tasks_table.setItem(row, 0, QTableWidgetItem(task.name))
            self.tasks_table.setItem(row, 1, QTableWidgetItem(task.status.value))
            self.tasks_table.setItem(row, 2, QTableWidgetItem(task.c4d_file_path))
            self.tasks_table.setItem(row, 3, QTableWidgetItem(task.output_folder))
            self.tasks_table.setItem(row, 4, QTableWidgetItem(task.cinema4d_version))
            
            duration = ""
            if task.duration:
                duration = f"{task.duration:.1f}s"
            self.tasks_table.setItem(row, 5, QTableWidgetItem(duration))
    
    def update_ui(self):
        """Aktualizuje interfejs użytkownika"""
        # Aktualizacja tabeli zadań
        self.update_tasks_table()
        
        # Aktualizacja zasobów systemowych
        resources = self.resource_monitor.get_system_resources()
        self.cpu_label.setText(f"CPU: {resources['cpu']:.1f}%")
        self.memory_label.setText(f"RAM: {resources['memory']:.1f}%")
        self.disk_label.setText(f"Dysk: {resources['disk']:.1f}%")
    
    def on_task_started(self, task: RenderTask):
        """Callback wywoływany przy rozpoczęciu zadania"""
        self.log_text.append(f"[{task.started_at}] Rozpoczęto: {task.name}")
    
    def on_task_completed(self, task: RenderTask):
        """Callback wywoływany przy zakończeniu zadania"""
        self.log_text.append(f"[{task.completed_at}] Zakończono: {task.name} (czas: {task.duration:.1f}s)")
    
    def on_task_failed(self, task: RenderTask):
        """Callback wywoływany przy błędzie zadania"""
        self.log_text.append(f"[{task.completed_at}] Błąd: {task.name} - {task.error_message}")
Plik: utils/resource_monitor.py
Opis: Monitor zasobów systemowych dla optymalizacji renderingu
pythonimport psutil
import logging
from typing import Dict

class ResourceMonitor:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def get_system_resources(self) -> Dict[str, float]:
        """Zwraca aktualny stan zasobów systemowych"""
        try:
            return {
                'cpu': psutil.cpu_percent(interval=1),
                'memory': psutil.virtual_memory().percent,
                'disk': psutil.disk_usage('/').percent
            }
        except Exception as e:
            self.logger.error(f"Błąd odczytu zasobów systemowych: {str(e)}")
            return {'cpu': 0, 'memory': 0, 'disk': 0}
    
    def should_start_render(self) -> bool:
        """Określa czy system jest gotowy do rozpoczęcia renderingu"""
        resources = self.get_system_resources()
        
        # Proste heurystyki - można rozbudować
        if resources['cpu'] > 90:
            return False
        if resources['memory'] > 85:
            return False
        if resources['disk'] > 95:
            return False
            
        return True
    
    def get_optimal_thread_count(self) -> int:
        """Zwraca optymalną liczbę wątków do renderingu"""
        cpu_count = psutil.cpu_count(logical=False)
        memory_gb = psutil.virtual_memory().total / (1024**3)
        
        # Prosty algorytm - można dostosować
        if memory_gb < 8:
            return max(1, cpu_count - 2)
        elif memory_gb < 16:
            return max(1, cpu_count - 1)
        else:
            return cpu_count
Dodatkowe pliki potrzebne do implementacji:

gui/task_dialog.py - Dialog dodawania/edycji zadań
utils/logger.py - Konfiguracja systemu logowania
utils/file_monitor.py - Monitorowanie plików wyjściowych
utils/email_reporter.py - Wysyłanie raportów email
requirements.txt - Lista wymaganych pakietów

Czy chciałbyś, żebym rozwinął któryś z tych modułów lub omówił szczegóły implementacji?