from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.queue_manager import QueueManager
from gui.button_styles import BUTTON_STYLES
from gui.preferences_dialog import PreferencesDialog
from gui.task_dialog import TaskDialog
from models.task import RenderTask
from utils.resource_monitor import ResourceMonitor


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.queue_manager = QueueManager()
        self.resource_monitor = ResourceMonitor()
        self.init_ui()
        self.setup_connections()
        self.setup_timer()
        self.apply_styles()

    def init_ui(self):
        """Inicjalizuje interfejs użytkownika"""
        self.setWindowTitle("Cinema 4D Batch Renderer")
        self.setGeometry(100, 100, 1200, 800)
        self.setStyleSheet("background-color: #1E1E1E; color: #CCCCCC;")

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
        self.preferences_btn = QPushButton("Preferencje")

        toolbar_layout.addWidget(self.add_task_btn)
        toolbar_layout.addWidget(self.remove_task_btn)
        toolbar_layout.addWidget(self.start_queue_btn)
        toolbar_layout.addWidget(self.stop_queue_btn)
        toolbar_layout.addStretch()
        toolbar_layout.addWidget(self.preferences_btn)

        main_layout.addLayout(toolbar_layout)

        # Splitter dla głównego obszaru
        splitter = QSplitter()
        main_layout.addWidget(splitter)

        # Tabela zadań
        self.tasks_table = QTableWidget()
        self.tasks_table.setColumnCount(6)
        self.tasks_table.setHorizontalHeaderLabels(
            ["Nazwa", "Status", "Plik C4D", "Folder wyjściowy", "Wersja C4D", "Czas"]
        )
        self.tasks_table.setStyleSheet(
            """
            QTableWidget {
                background-color: #252526;
                color: #CCCCCC;
                gridline-color: #3F3F46;
                border: 1px solid #3F3F46;
            }
            QHeaderView::section {
                background-color: #2D2D2D;
                color: #CCCCCC;
                padding: 4px;
                border: 1px solid #3F3F46;
            }
            QTableWidget::item {
                padding: 4px;
            }
            QTableWidget::item:selected {
                background-color: #007ACC;
            }
        """
        )
        splitter.addWidget(self.tasks_table)

        # Panel informacyjny
        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)

        # Zasoby systemowe
        resources_group = QGroupBox("Zasoby systemowe")
        resources_group.setStyleSheet(
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
        logs_group.setStyleSheet(
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
        logs_layout = QVBoxLayout(logs_group)
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(300)
        self.log_text.setStyleSheet(
            """
            QTextEdit {
                background-color: #1E1E1E;
                color: #CCCCCC;
                border: 1px solid #3F3F46;
                border-radius: 2px;
            }
        """
        )
        logs_layout.addWidget(self.log_text)
        info_layout.addWidget(logs_group)

        splitter.addWidget(info_widget)
        splitter.setSizes([800, 400])

        # Status bar
        self.statusBar().setStyleSheet(
            """
            QStatusBar {
                background-color: #252526;
                color: #CCCCCC;
                border-top: 1px solid #3F3F46;
            }
        """
        )
        self.statusBar().showMessage("Gotowy")

    def apply_styles(self):
        """Aplikuje style do przycisków"""
        self.add_task_btn.setStyleSheet(BUTTON_STYLES["primary"])
        self.remove_task_btn.setStyleSheet(BUTTON_STYLES["warning"])
        self.start_queue_btn.setStyleSheet(BUTTON_STYLES["success"])
        self.stop_queue_btn.setStyleSheet(BUTTON_STYLES["stop"])
        self.preferences_btn.setStyleSheet(BUTTON_STYLES["default"])
        self.stop_queue_btn.setEnabled(False)

    def setup_connections(self):
        """Konfiguruje połączenia sygnałów"""
        self.add_task_btn.clicked.connect(self.add_task)
        self.remove_task_btn.clicked.connect(self.remove_task)
        self.start_queue_btn.clicked.connect(self.start_queue)
        self.stop_queue_btn.clicked.connect(self.stop_queue)
        self.preferences_btn.clicked.connect(self.show_preferences)

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
        if dialog.exec() == dialog.accepted:
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
        self.log_text.append(
            f"[{task.completed_at}] Zakończono: {task.name} "
            f"(czas: {task.duration:.1f}s)"
        )

    def on_task_failed(self, task: RenderTask):
        """Callback wywoływany przy błędzie zadania"""
        self.log_text.append(
            f"[{task.completed_at}] Błąd: {task.name} - {task.error_message}"
        )

    def show_preferences(self):
        """Otwiera okno preferencji"""
        dialog = PreferencesDialog(self)
        if dialog.exec() == dialog.accepted:
            # TODO: Zapisz zmiany w konfiguracji
            pass
