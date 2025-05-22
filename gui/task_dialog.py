import uuid

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from core.cinema4d_controller import Cinema4DController
from gui.button_styles import BUTTON_STYLES
from models.task import RenderTask


class TaskDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.c4d_controller = Cinema4DController()
        self.init_ui()
        self.apply_styles()

    def init_ui(self):
        """Inicjalizuje interfejs użytkownika"""
        self.setWindowTitle("Dodaj zadanie")
        self.setMinimumWidth(400)
        self.setStyleSheet(
            """
            QDialog {
                background-color: #1E1E1E;
                color: #CCCCCC;
            }
            QLabel {
                color: #CCCCCC;
            }
            QLineEdit, QComboBox, QSpinBox {
                background-color: #252526;
                color: #CCCCCC;
                border: 1px solid #3F3F46;
                border-radius: 2px;
                padding: 4px;
                min-height: 24px;
            }
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
                border-color: #007ACC;
            }
        """
        )

        layout = QVBoxLayout(self)

        # Formularz
        form_layout = QFormLayout()

        self.name_edit = QLineEdit()
        form_layout.addRow("Nazwa:", self.name_edit)

        self.c4d_file_edit = QLineEdit()
        self.c4d_file_btn = QPushButton("...")
        c4d_file_layout = QHBoxLayout()
        c4d_file_layout.addWidget(self.c4d_file_edit)
        c4d_file_layout.addWidget(self.c4d_file_btn)
        form_layout.addRow("Plik C4D:", c4d_file_layout)

        self.output_folder_edit = QLineEdit()
        self.output_folder_btn = QPushButton("...")
        output_folder_layout = QHBoxLayout()
        output_folder_layout.addWidget(self.output_folder_edit)
        output_folder_layout.addWidget(self.output_folder_btn)
        form_layout.addRow("Folder wyjściowy:", output_folder_layout)

        self.c4d_version_combo = QComboBox()
        self.c4d_version_combo.addItems(self.c4d_controller.c4d_installations.keys())
        form_layout.addRow("Wersja C4D:", self.c4d_version_combo)

        self.start_frame_spin = QSpinBox()
        self.start_frame_spin.setRange(0, 9999)
        form_layout.addRow("Start klatki:", self.start_frame_spin)

        self.end_frame_spin = QSpinBox()
        self.end_frame_spin.setRange(0, 9999)
        form_layout.addRow("Koniec klatki:", self.end_frame_spin)

        layout.addLayout(form_layout)

        # Przyciski
        button_layout = QHBoxLayout()
        self.ok_button = QPushButton("OK")
        self.cancel_button = QPushButton("Anuluj")
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)

        # Połączenia
        self.c4d_file_btn.clicked.connect(self.browse_c4d_file)
        self.output_folder_btn.clicked.connect(self.browse_output_folder)
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

    def apply_styles(self):
        """Aplikuje style do przycisków"""
        self.c4d_file_btn.setStyleSheet(BUTTON_STYLES["default"])
        self.output_folder_btn.setStyleSheet(BUTTON_STYLES["default"])
        self.ok_button.setStyleSheet(BUTTON_STYLES["primary"])
        self.cancel_button.setStyleSheet(BUTTON_STYLES["default"])

    def browse_c4d_file(self):
        """Otwiera dialog wyboru pliku C4D"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Wybierz plik Cinema 4D", "", "Cinema 4D Files (*.c4d)"
        )
        if file_path:
            self.c4d_file_edit.setText(file_path)

    def browse_output_folder(self):
        """Otwiera dialog wyboru folderu wyjściowego"""
        folder_path = QFileDialog.getExistingDirectory(self, "Wybierz folder wyjściowy")
        if folder_path:
            self.output_folder_edit.setText(folder_path)

    def get_task(self) -> RenderTask:
        """Tworzy i zwraca nowe zadanie na podstawie danych z formularza"""
        return RenderTask(
            id=str(uuid.uuid4()),
            name=self.name_edit.text(),
            c4d_file_path=self.c4d_file_edit.text(),
            output_folder=self.output_folder_edit.text(),
            cinema4d_version=self.c4d_version_combo.currentText(),
            start_frame=self.start_frame_spin.value(),
            end_frame=self.end_frame_spin.value(),
        )
