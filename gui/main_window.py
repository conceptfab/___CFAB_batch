from PyQt6.QtCore import QThread, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
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
from gui.worker_status_widget import WorkerStatusWidget
from models.task import RenderTask, TaskStatus
from utils.logger import setup_logger
from utils.resource_monitor import ResourceMonitor


class ResourceMonitorThread(QThread):
    """Wątek do monitorowania zasobów systemowych"""

    resources_updated = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.resource_monitor = ResourceMonitor()
        self.running = True

    def run(self):
        while self.running:
            resources = self.resource_monitor.get_system_resources()
            self.resources_updated.emit(resources)
            self.msleep(2000)  # Sprawdź co 2 sekundy

    def stop(self):
        self.running = False
        self.quit()
        self.wait()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.queue_manager = QueueManager()
        self.resource_monitor = ResourceMonitor()
        self.logger = setup_logger("main_window")
        self.init_ui()
        self.setup_connections()
        self.setup_timers()
        self.setup_resource_monitoring()
        self.apply_styles()

        # Wczytaj zadania z folderu tasks
        self.queue_manager.load_tasks()
        self.update_tasks_table()  # Aktualizuj widok po wczytaniu zadań

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
        self.edit_task_btn = QPushButton("Edytuj zadanie")

        toolbar_layout.addWidget(self.add_task_btn)
        toolbar_layout.addWidget(self.remove_task_btn)
        toolbar_layout.addWidget(self.start_queue_btn)
        toolbar_layout.addWidget(self.stop_queue_btn)
        toolbar_layout.addWidget(self.edit_task_btn)
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

        # Status workerów
        self.worker_status_widget = WorkerStatusWidget()
        info_layout.addWidget(self.worker_status_widget)

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
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet(
            """
            QTextEdit {
                background-color: #1E1E1E;
                color: #CCCCCC;
                border: 1px solid #3F3F46;
                border-radius: 2px;
                margin: 4px;
            }
        """
        )
        logs_layout.addWidget(self.log_text)
        logs_layout.setContentsMargins(4, 4, 4, 4)  # Dodaję marginesy
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
        self.edit_task_btn.clicked.connect(self.edit_task)

        # Callbacks dla queue managera
        self.queue_manager.on_task_started = self.on_task_started
        self.queue_manager.on_task_completed = self.on_task_completed
        self.queue_manager.on_task_failed = self.on_task_failed

        # Callback dla logów Cinema 4D
        self.queue_manager.c4d_controller.on_log_message = self.on_cinema4d_log

    def setup_timers(self):
        """Konfiguruje timery dla aktualizacji UI"""
        # Timer dla tabeli zadań (rzadziej)
        self.tasks_timer = QTimer()
        self.tasks_timer.timeout.connect(self.update_tasks_table)
        self.tasks_timer.start(5000)  # Co 5 sekund

        # Timer dla statusu workerów (częściej)
        self.workers_timer = QTimer()
        self.workers_timer.timeout.connect(self.update_worker_status)
        self.workers_timer.start(2000)  # Co 2 sekundy

    def setup_resource_monitoring(self):
        """Konfiguruje asynchroniczny monitoring zasobów"""
        self.resource_thread = ResourceMonitorThread()
        self.resource_thread.resources_updated.connect(self.update_resources)
        self.resource_thread.start()

    def add_task(self):
        """Otwiera dialog dodawania zadania"""
        try:
            dialog = TaskDialog(self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                task = dialog.get_task()
                self.queue_manager.add_task(task)
                self.update_tasks_table()
                self.statusBar().showMessage(f"Dodano zadanie: {task.name}")
        except ValueError as e:
            QMessageBox.warning(self, "Błąd", str(e))
        except Exception as e:
            self.logger.error(f"Błąd podczas dodawania zadania: {str(e)}")
            QMessageBox.critical(self, "Błąd", f"Wystąpił błąd: {str(e)}")

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
        """Aktualizuje tabelę zadań (zoptymalizowane)"""
        tasks = self.queue_manager.get_tasks()

        # Sprawdź czy liczba zadań się zmieniła
        if self.tasks_table.rowCount() != len(tasks):
            self.tasks_table.setRowCount(len(tasks))

        for row, task in enumerate(tasks):
            # Aktualizuj tylko zmienione komórki
            self._update_table_cell(row, 0, task.name)
            self._update_table_cell(row, 1, task.status.value)
            self._update_table_cell(row, 2, task.c4d_file_path)
            self._update_table_cell(row, 3, task.output_folder)
            self._update_table_cell(row, 4, task.cinema4d_version)

            duration = f"{task.duration:.1f}s" if task.duration else ""
            self._update_table_cell(row, 5, duration)

    def _update_table_cell(self, row: int, col: int, text: str):
        """Aktualizuje komórkę tylko jeśli wartość się zmieniła"""
        item = self.tasks_table.item(row, col)
        if item is None:
            self.tasks_table.setItem(row, col, QTableWidgetItem(text))
        elif item.text() != text:
            item.setText(text)

    def update_ui(self):
        """Lekka aktualizacja UI - usuń ciężkie operacje"""
        # Usuń aktualizację tabeli i zasobów - mają własne timery
        pass

    def update_worker_status(self):
        """Aktualizuje tylko status workerów"""
        workers = self.queue_manager.get_worker_status()
        self.worker_status_widget.update_workers(workers)

    def update_resources(self, resources: dict):
        """Aktualizuje wyświetlanie zasobów (wywoływane przez sygnał)"""
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

    def on_cinema4d_log(self, message: str):
        """Obsługuje logi z Cinema 4D"""
        self.log_text.append(message)
        # Przewiń do końca
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )

    def show_preferences(self):
        """Otwiera okno preferencji"""
        dialog = PreferencesDialog(self)
        if dialog.exec() == dialog.accepted:
            # TODO: Zapisz zmiany w konfiguracji
            pass

    def edit_task(self):
        """Otwiera dialog edycji wybranego zadania (tylko PENDING)"""
        current_row = self.tasks_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Błąd", "Nie wybrano zadania do edycji.")
            return
        task = self.queue_manager.tasks[current_row]
        if task.status != TaskStatus.PENDING:
            QMessageBox.warning(
                self, "Błąd", "Można edytować tylko zadania o statusie 'pending'."
            )
            return
        # Otwórz dialog z wypełnionymi polami
        dialog = TaskDialog(self)
        dialog.name_edit.setText(task.name)
        dialog.c4d_file_edit.setText(task.c4d_file_path)
        dialog.c4d_version_combo.setCurrentText(task.cinema4d_version)
        dialog.image_output_edit.setText(task.output_folder)
        if task.start_frame is not None and task.end_frame is not None:
            if task.start_frame == task.end_frame:
                dialog.frames_edit.setText(str(task.start_frame))
            else:
                dialog.frames_edit.setText(f"{task.start_frame}-{task.end_frame}")
        # render_settings
        rs = task.render_settings
        dialog.threads_spin.setValue(rs.get("threads", 8))
        dialog.use_gpu.setChecked(rs.get("use_gpu", False))
        dialog.no_gui.setChecked(rs.get("no_gui", False))
        dialog.batch_mode.setChecked(rs.get("batch_mode", False))
        dialog.shutdown.setChecked(rs.get("shutdown", False))
        dialog.quit.setChecked(rs.get("quit", False))
        dialog.debug_mode.setChecked(rs.get("debug_mode", False))
        dialog.show_console.setChecked(rs.get("show_console", False))
        dialog.log_file_edit.setText(rs.get("log_file", ""))
        dialog.verbose.setChecked(rs.get("verbose", False))
        dialog.memory_limit.setValue(rs.get("memory_limit", 4096))
        dialog.priority_combo.setCurrentText(rs.get("priority", "high"))
        dialog.update_command_preview()
        if dialog.exec() == QDialog.DialogCode.Accepted:
            try:
                new_task = dialog.get_task()
                new_task.id = task.id  # zachowaj ten sam ID
                self.queue_manager.edit_task(task.id, new_task)
                self.update_tasks_table()
                self.statusBar().showMessage(f"Zmieniono zadanie: {new_task.name}")
            except Exception as e:
                QMessageBox.critical(
                    self, "Błąd", f"Nie udało się edytować zadania: {e}"
                )

    def closeEvent(self, event):
        """Obsługuje zamknięcie okna"""
        if hasattr(self, "resource_thread"):
            self.resource_thread.stop()
        super().closeEvent(event)
