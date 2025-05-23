from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGroupBox,
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
        self.load_logging_settings()

    def init_ui(self):
        """Inicjalizuje interfejs użytkownika"""
        self.setWindowTitle("Preferencje")
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)
        self.setStyleSheet("background-color: #1E1E1E; color: #CCCCCC;")

        layout = QVBoxLayout(self)

        # Sekcja wersji Cinema 4D
        versions_group = QGroupBox("Wersje Cinema 4D")
        versions_layout = QVBoxLayout(versions_group)

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
        versions_layout.addWidget(self.versions_table)

        # Przyciski zarządzania wersjami
        versions_buttons_layout = QHBoxLayout()
        self.add_btn = QPushButton("Dodaj wersję")
        self.edit_btn = QPushButton("Edytuj")
        self.remove_btn = QPushButton("Usuń")
        self.browse_btn = QPushButton("Przeglądaj...")

        versions_buttons_layout.addWidget(self.add_btn)
        versions_buttons_layout.addWidget(self.edit_btn)
        versions_buttons_layout.addWidget(self.remove_btn)
        versions_buttons_layout.addWidget(self.browse_btn)
        versions_buttons_layout.addStretch()

        versions_layout.addLayout(versions_buttons_layout)
        layout.addWidget(versions_group)

        # Sekcja logowania
        logging_group = QGroupBox("Ustawienia logowania")
        logging_layout = QFormLayout(logging_group)

        self.log_to_file_checkbox = QCheckBox("Zapisuj logi do pliku")
        logging_layout.addRow("", self.log_to_file_checkbox)

        # Ścieżka pliku logu
        log_file_layout = QHBoxLayout()
        self.log_file_edit = QLineEdit()
        self.log_file_edit.setEnabled(False)  # Domyślnie wyłączone
        self.log_file_browse_btn = QPushButton("Przeglądaj...")
        self.log_file_browse_btn.setEnabled(False)  # Domyślnie wyłączone

        log_file_layout.addWidget(self.log_file_edit)
        log_file_layout.addWidget(self.log_file_browse_btn)
        logging_layout.addRow("Plik logu:", log_file_layout)

        layout.addWidget(logging_group)

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
        self.log_to_file_checkbox.stateChanged.connect(self.on_log_to_file_changed)
        self.log_file_browse_btn.clicked.connect(self.browse_log_file)
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

    def on_log_to_file_changed(self, state):
        """Obsługuje zmianę stanu checkboxa logowania do pliku"""
        enabled = state == 2  # Qt.CheckState.Checked
        self.log_file_edit.setEnabled(enabled)
        self.log_file_browse_btn.setEnabled(enabled)

    def browse_log_file(self):
        """Otwiera dialog wyboru pliku logu"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Wybierz plik logu",
            "logs/app.log",
            "Log Files (*.log);;Text Files (*.txt);;All Files (*.*)",
        )
        if file_path:
            self.log_file_edit.setText(file_path)

    def load_logging_settings(self):
        """Ładuje ustawienia logowania"""
        log_to_file, log_file_path = self.config.get_logging_settings()
        self.log_to_file_checkbox.setChecked(log_to_file)
        if log_file_path:
            self.log_file_edit.setText(log_file_path)

    def apply_styles(self):
        """Aplikuje style do przycisków"""
        self.add_btn.setStyleSheet(BUTTON_STYLES["primary"])
        self.edit_btn.setStyleSheet(BUTTON_STYLES["default"])
        self.remove_btn.setStyleSheet(BUTTON_STYLES["warning"])
        self.browse_btn.setStyleSheet(BUTTON_STYLES["default"])
        self.log_file_browse_btn.setStyleSheet(BUTTON_STYLES["default"])
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
            version_item = self.versions_table.item(row, 0)
            path_item = self.versions_table.item(row, 1)
            if version_item and path_item:
                version = version_item.text()
                path = path_item.text()
                if version and path:
                    versions[version] = path
        return versions

    def accept(self):
        """Zapisuje zmiany i zamyka okno"""
        versions = self.get_versions()
        self.config.set_c4d_versions(versions)

        # Zapisz ustawienia logowania
        log_to_file = self.log_to_file_checkbox.isChecked()
        log_file_path = self.log_file_edit.text() if log_to_file else None
        self.config.set_logging_settings(log_to_file, log_file_path)

        super().accept()
