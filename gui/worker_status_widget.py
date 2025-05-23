from PyQt6.QtCore import QTimer
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
