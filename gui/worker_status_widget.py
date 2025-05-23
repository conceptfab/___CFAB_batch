from PyQt6.QtWidgets import QGroupBox, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from models.task import RenderTask


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

    def update_workers(self, workers: list[dict]):
        """Aktualizuje wyświetlanie statusu workerów (zoptymalizowane)"""
        # Nie przebudowuj całego layoutu za każdym razem
        current_count = self.workers_layout.count()
        needed_count = len(workers)

        # Dodaj brakujące widżety
        for i in range(current_count, needed_count):
            worker_widget = self._create_worker_widget()
            self.workers_layout.addWidget(worker_widget)

        # Usuń nadmiarowe widżety
        for i in range(needed_count, current_count):
            item = self.workers_layout.takeAt(needed_count)
            if item and item.widget():
                item.widget().deleteLater()

        # Aktualizuj istniejące widżety
        for i, worker in enumerate(workers):
            worker_widget = self.workers_layout.itemAt(i).widget()
            if worker_widget:
                self._update_worker_widget(worker_widget, worker)

    def _create_worker_widget(self) -> QWidget:
        """Tworzy nowy widżet workera"""
        worker_widget = QWidget()
        worker_layout = QHBoxLayout(worker_widget)

        worker_label = QLabel()
        status_label = QLabel()

        worker_layout.addWidget(worker_label)
        worker_layout.addWidget(status_label)
        worker_layout.addStretch()

        # Zapisz referencje do labelek
        worker_widget.worker_label = worker_label
        worker_widget.status_label = status_label

        return worker_widget

    def _update_worker_widget(self, widget: QWidget, worker: dict):
        """Aktualizuje istniejący widżet workera"""
        widget.worker_label.setText(f"Worker {worker['worker_id']}:")

        if worker["is_busy"] and worker["current_task"]:
            task: RenderTask = worker["current_task"]
            text = f"Renderuje: {task.name}"
            color = "#10B981"  # Zielony
        else:
            text = "Bezczynny"
            color = "#9CA3AF"  # Szary

        widget.status_label.setText(text)
        widget.status_label.setStyleSheet(f"color: {color};")
