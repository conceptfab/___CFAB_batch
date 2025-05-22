from PyQt6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from core.config import Config
from gui.button_styles import BUTTON_STYLES


class PreferencesDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = Config()
        self.init_ui()
        self.apply_styles()
        self.load_versions()

    def init_ui(self):
        """Inicjalizuje interfejs użytkownika"""
        self.setWindowTitle("Preferencje")
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)
        self.setStyleSheet("background-color: #1E1E1E; color: #CCCCCC;")

        layout = QVBoxLayout(self)

        # Tabela wersji
        self.versions_table = QTableWidget()
        self.versions_table.setColumnCount(2)
        self.versions_table.setHorizontalHeaderLabels(
            ["Wersja", "Ścieżka do pliku wykonywalnego"]
        )
        self.versions_table.setStyleSheet(
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
        layout.addWidget(self.versions_table)

        # Przyciski zarządzania
        buttons_layout = QHBoxLayout()

        self.add_btn = QPushButton("Dodaj wersję")
        self.edit_btn = QPushButton("Edytuj")
        self.remove_btn = QPushButton("Usuń")
        self.browse_btn = QPushButton("Przeglądaj...")

        buttons_layout.addWidget(self.add_btn)
        buttons_layout.addWidget(self.edit_btn)
        buttons_layout.addWidget(self.remove_btn)
        buttons_layout.addWidget(self.browse_btn)
        buttons_layout.addStretch()

        layout.addLayout(buttons_layout)

        # Przyciski OK/Anuluj
        dialog_buttons = QHBoxLayout()
        self.ok_button = QPushButton("OK")
        self.cancel_button = QPushButton("Anuluj")
        dialog_buttons.addWidget(self.ok_button)
        dialog_buttons.addWidget(self.cancel_button)
        layout.addLayout(dialog_buttons)

        # Połączenia
        self.add_btn.clicked.connect(self.add_version)
        self.edit_btn.clicked.connect(self.edit_version)
        self.remove_btn.clicked.connect(self.remove_version)
        self.browse_btn.clicked.connect(self.browse_executable)
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

    def apply_styles(self):
        """Aplikuje style do przycisków"""
        self.add_btn.setStyleSheet(BUTTON_STYLES["primary"])
        self.edit_btn.setStyleSheet(BUTTON_STYLES["default"])
        self.remove_btn.setStyleSheet(BUTTON_STYLES["warning"])
        self.browse_btn.setStyleSheet(BUTTON_STYLES["default"])
        self.ok_button.setStyleSheet(BUTTON_STYLES["primary"])
        self.cancel_button.setStyleSheet(BUTTON_STYLES["default"])

    def load_versions(self):
        """Ładuje listę wersji Cinema 4D"""
        versions = self.config.get_c4d_versions()
        self.versions_table.setRowCount(len(versions))

        for row, (version, path) in enumerate(versions.items()):
            self.versions_table.setItem(row, 0, QTableWidgetItem(version))
            self.versions_table.setItem(row, 1, QTableWidgetItem(path))

    def add_version(self):
        """Dodaje nową wersję Cinema 4D"""
        row = self.versions_table.rowCount()
        self.versions_table.insertRow(row)
        self.versions_table.setItem(row, 0, QTableWidgetItem(""))
        self.versions_table.setItem(row, 1, QTableWidgetItem(""))
        self.versions_table.editItem(self.versions_table.item(row, 0))

    def edit_version(self):
        """Edytuje wybraną wersję Cinema 4D"""
        current_row = self.versions_table.currentRow()
        if current_row >= 0:
            self.versions_table.editItem(self.versions_table.item(current_row, 0))

    def remove_version(self):
        """Usuwa wybraną wersję Cinema 4D"""
        current_row = self.versions_table.currentRow()
        if current_row >= 0:
            reply = QMessageBox.question(
                self,
                "Potwierdzenie",
                "Czy na pewno chcesz usunąć wybraną wersję?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.versions_table.removeRow(current_row)

    def browse_executable(self):
        """Otwiera dialog wyboru pliku wykonywalnego Cinema 4D"""
        current_row = self.versions_table.currentRow()
        if current_row >= 0:
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Wybierz plik wykonywalny Cinema 4D",
                "",
                "Executable Files (*.exe)",
            )
            if file_path:
                self.versions_table.setItem(current_row, 1, QTableWidgetItem(file_path))

    def get_versions(self):
        """Zwraca słownik wersji Cinema 4D"""
        versions = {}
        for row in range(self.versions_table.rowCount()):
            version = self.versions_table.item(row, 0).text()
            path = self.versions_table.item(row, 1).text()
            if version and path:
                versions[version] = path
        return versions

    def accept(self):
        """Zapisuje zmiany i zamyka okno"""
        versions = self.get_versions()
        self.config.set_c4d_versions(versions)
        super().accept()
