Zmiany w kodzie
1. Poprawka logovani w utils/logger.py
Problem: Obecnie logi są automatycznie zapisywane do pliku, a opcja logowania do pliku powinna być konfigurowalna w preferencjach.
pythonimport logging
import os
from datetime import datetime
from typing import Optional


def setup_logger(name: str, log_to_file: bool = False, log_file_path: Optional[str] = None) -> logging.Logger:
    """Konfiguruje i zwraca logger dla podanego modułu"""
    logger = logging.getLogger(name)

    # Usuń istniejące handlery, aby uniknąć duplikowania
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    logger.setLevel(logging.INFO)

    # Handler do konsoli - zawsze aktywny
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # Format logów z czasem i nazwą modułu
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(message)s', 
                                datefmt='%H:%M:%S')
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Handler do pliku - tylko jeśli włączony w preferencjach
    if log_to_file:
        # Tworzenie katalogu na logi jeśli nie istnieje
        log_dir = "logs"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        # Użyj podanej ścieżki lub domyślnej
        if log_file_path:
            file_path = log_file_path
        else:
            file_path = os.path.join(log_dir, f"{datetime.now().strftime('%Y%m%d')}.log")
        
        file_handler = logging.FileHandler(file_path, encoding="utf-8")
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger
2. Rozszerzenie konfiguracji w core/config.py
Problem: Brak opcji konfiguracji logowania do pliku.
pythonimport json
import os
from typing import Dict, Optional


class Config:
    def __init__(self):
        self.config_file = "config.json"
        self.c4d_versions: Dict[str, str] = {}
        self.log_to_file: bool = False
        self.log_file_path: Optional[str] = None
        self.load_config()

    def load_config(self):
        """Ładuje konfigurację z pliku"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.c4d_versions = data.get("c4d_versions", {})
                    self.log_to_file = data.get("log_to_file", False)
                    self.log_file_path = data.get("log_file_path", None)
            except Exception as e:
                print(f"Błąd ładowania konfiguracji: {str(e)}")
                self.c4d_versions = {}
                self.log_to_file = False
                self.log_file_path = None

    def save_config(self):
        """Zapisuje konfigurację do pliku"""
        try:
            data = {
                "c4d_versions": self.c4d_versions,
                "log_to_file": self.log_to_file,
                "log_file_path": self.log_file_path
            }
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Błąd zapisywania konfiguracji: {str(e)}")

    def get_c4d_versions(self) -> Dict[str, str]:
        """Zwraca słownik wersji Cinema 4D"""
        return self.c4d_versions

    def set_c4d_versions(self, versions: Dict[str, str]):
        """Ustawia słownik wersji Cinema 4D"""
        self.c4d_versions = versions
        self.save_config()

    def get_logging_settings(self) -> tuple[bool, Optional[str]]:
        """Zwraca ustawienia logowania"""
        return self.log_to_file, self.log_file_path

    def set_logging_settings(self, log_to_file: bool, log_file_path: Optional[str] = None):
        """Ustawia opcje logowania"""
        self.log_to_file = log_to_file
        self.log_file_path = log_file_path
        self.save_config()
3. Rozszerzenie okna preferencji w gui/preferences_dialog.py
Problem: Brak opcji konfiguracji logowania w interfejsie użytkownika.
pythonfrom PyQt6.QtWidgets import (
    QCheckBox,
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
    QGroupBox,
    QFormLayout,
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
4. Aktualizacja głównego okna w gui/main_window.py
Problem: Brak uwzględnienia konfiguracji logowania i restartowania loggerów po zmianie ustawień.
python# Dodaj na początku klasy MainWindow
def __init__(self):
    super().__init__()
    self.config = Config()
    self.setup_logging()
    # ... reszta inicjalizacji
    
def setup_logging(self):
    """Konfiguruje logowanie na podstawie ustawień"""
    log_to_file, log_file_path = self.config.get_logging_settings()
    self.logger = setup_logger("main_window", log_to_file, log_file_path)
    
    # Skonfiguruj również loggery dla innych komponentów
    self.queue_manager = QueueManager()
    self.queue_manager.logger = setup_logger("queue_manager", log_to_file, log_file_path)
    self.queue_manager.c4d_controller.logger = setup_logger("cinema4d_controller", log_to_file, log_file_path)

def show_preferences(self):
    """Otwiera okno preferencji"""
    dialog = PreferencesDialog(self)
    if dialog.exec() == QDialog.DialogCode.Accepted:
        # Przeładuj konfigurację logowania
        self.setup_logging()
        # Przeładuj ustawienia w queue_manager
        self.queue_manager.c4d_controller = Cinema4DController()
        self.statusBar().showMessage("Ustawienia zostały zapisane")
5. Aktualizacja pozostałych modułów
Problem: Inne moduły muszą używać nowego systemu logowania.
W plikach core/queue_manager.py, core/cinema4d_controller.py i innych, zmień inicjalizację loggerów:
python# Zamiast:
self.logger = setup_logger("nazwa_modulu")

# Użyj:
from core.config import Config
config = Config()
log_to_file, log_file_path = config.get_logging_settings()
self.logger = setup_logger("nazwa_modulu", log_to_file, log_file_path)
Podsumowanie głównych poprawek:

Konfigurowalne logowanie do pliku - opcja w preferencjach
Wszystkie logi w konsoli i UI - zawsze aktywne
Lepszy format logów - z czasem i nazwą modułu
Dynamiczne przeładowanie loggerów - po zmianie ustawień
Rozszerzone okno preferencji - z sekcją logowania

Te zmiany zapewnią większą kontrolę nad systemem logowania i lepszą użyteczność aplikacji.