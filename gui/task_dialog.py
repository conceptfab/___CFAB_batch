import uuid

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
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
        self.update_command_preview()

    def init_ui(self):
        """Inicjalizuje interfejs użytkownika"""
        self.setWindowTitle("Dodaj zadanie")
        self.setMinimumWidth(800)  # Zwiększona szerokość
        self.setStyleSheet(
            """
            QDialog {
                background-color: #1E1E1E;
                color: #CCCCCC;
            }
            QLabel {
                color: #CCCCCC;
            }
            QLineEdit, QComboBox, QSpinBox, QTextEdit {
                background-color: #252526;
                color: #CCCCCC;
                border: 1px solid #3F3F46;
                border-radius: 2px;
                padding: 4px;
                min-height: 24px;
            }
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QTextEdit:focus {
                border-color: #007ACC;
            }
            QGroupBox {
                color: #CCCCCC;
                border: 1px solid #3F3F46;
                margin-top: 1em;
                padding-top: 1em;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px;
            }
            QTabWidget::pane {
                border: 1px solid #3F3F46;
            }
            QTabBar::tab {
                background-color: #2D2D2D;
                color: #CCCCCC;
                padding: 8px 16px;
                border: 1px solid #3F3F46;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: #1E1E1E;
                border-bottom: 1px solid #1E1E1E;
            }
        """
        )

        layout = QVBoxLayout(self)

        # Formularz podstawowy
        form_layout = QFormLayout()

        self.name_edit = QLineEdit()
        form_layout.addRow("Nazwa:", self.name_edit)

        # Plik C4D z checkboxem
        c4d_file_layout = QHBoxLayout()
        self.c4d_file_edit = QLineEdit()
        self.c4d_file_btn = QPushButton("...")
        self.use_file_settings = QCheckBox("Użyj ustawień plików")
        c4d_file_layout.addWidget(self.c4d_file_edit)
        c4d_file_layout.addWidget(self.c4d_file_btn)
        c4d_file_layout.addWidget(self.use_file_settings)
        form_layout.addRow("Plik C4D:", c4d_file_layout)

        # Wersja C4D
        self.c4d_version_combo = QComboBox()
        self.c4d_version_combo.addItems(self.c4d_controller.c4d_installations.keys())
        form_layout.addRow("Wersja C4D:", self.c4d_version_combo)

        layout.addLayout(form_layout)

        # Zakładki z parametrami
        self.tab_widget = QTabWidget()

        # Zakładka Renderowanie
        render_tab = QWidget()
        render_layout = QVBoxLayout(render_tab)

        # Grupa klatek
        frames_group = QGroupBox("Klatki")
        frames_layout = QFormLayout()
        self.frames_edit = QLineEdit()
        self.frames_edit.setPlaceholderText("np. 1, 1-100, 1,5,10")
        frames_layout.addRow("Zakres klatek:", self.frames_edit)
        frames_group.setLayout(frames_layout)
        render_layout.addWidget(frames_group)

        # Grupa wyjścia
        output_group = QGroupBox("Wyjście")
        output_layout = QFormLayout()

        # Obrazy
        image_layout = QHBoxLayout()
        self.image_output_edit = QLineEdit()
        self.image_output_btn = QPushButton("...")
        image_layout.addWidget(self.image_output_edit)
        image_layout.addWidget(self.image_output_btn)
        output_layout.addRow("Ścieżka obrazów:", image_layout)

        # Multipass
        multipass_layout = QHBoxLayout()
        self.multipass_output_edit = QLineEdit()
        self.multipass_output_btn = QPushButton("...")
        multipass_layout.addWidget(self.multipass_output_edit)
        multipass_layout.addWidget(self.multipass_output_btn)
        output_layout.addRow("Ścieżka multipass:", multipass_layout)

        output_group.setLayout(output_layout)
        render_layout.addWidget(output_group)

        # Grupa wydajności
        performance_group = QGroupBox("Wydajność")
        performance_layout = QFormLayout()

        self.threads_spin = QSpinBox()
        self.threads_spin.setRange(1, 64)
        self.threads_spin.setValue(8)
        performance_layout.addRow("Liczba wątków:", self.threads_spin)

        self.use_gpu = QCheckBox("Używaj GPU")
        performance_layout.addRow("", self.use_gpu)

        performance_group.setLayout(performance_layout)
        render_layout.addWidget(performance_group)

        self.tab_widget.addTab(render_tab, "Renderowanie")

        # Zakładka Tryb wsadowy
        batch_tab = QWidget()
        batch_layout = QVBoxLayout(batch_tab)

        self.no_gui = QCheckBox("Uruchom bez interfejsu (cmd-nogui)")
        self.batch_mode = QCheckBox("Tryb wsadowy (-batch)")
        self.shutdown = QCheckBox("Zamknij po zakończeniu (-shutdown)")
        self.quit = QCheckBox("Wyjdź po renderowaniu (-quit)")

        batch_layout.addWidget(self.no_gui)
        batch_layout.addWidget(self.batch_mode)
        batch_layout.addWidget(self.shutdown)
        batch_layout.addWidget(self.quit)
        batch_layout.addStretch()

        self.tab_widget.addTab(batch_tab, "Tryb wsadowy")

        # Zakładka Debugowanie
        debug_tab = QWidget()
        debug_layout = QVBoxLayout(debug_tab)

        self.debug_mode = QCheckBox("Tryb debugowania (cmd-debug)")
        self.show_console = QCheckBox("Pokaż konsolę (-console)")

        log_layout = QHBoxLayout()
        self.log_file_edit = QLineEdit()
        self.log_file_btn = QPushButton("...")
        log_layout.addWidget(self.log_file_edit)
        log_layout.addWidget(self.log_file_btn)

        self.verbose = QCheckBox("Szczegółowe komunikaty (-verbose)")

        debug_layout.addWidget(self.debug_mode)
        debug_layout.addWidget(self.show_console)
        debug_layout.addLayout(log_layout)
        debug_layout.addWidget(self.verbose)
        debug_layout.addStretch()

        self.tab_widget.addTab(debug_tab, "Debugowanie")

        # Zakładka Pamięć
        memory_tab = QWidget()
        memory_layout = QVBoxLayout(memory_tab)

        self.memory_limit = QSpinBox()
        self.memory_limit.setRange(1024, 32768)
        self.memory_limit.setValue(4096)
        self.memory_limit.setSingleStep(1024)

        self.priority_combo = QComboBox()
        self.priority_combo.addItems(["low", "normal", "high"])
        self.priority_combo.setCurrentText("high")

        memory_layout.addWidget(QLabel("Limit pamięci (MB):"))
        memory_layout.addWidget(self.memory_limit)
        memory_layout.addWidget(QLabel("Priorytet:"))
        memory_layout.addWidget(self.priority_combo)
        memory_layout.addStretch()

        self.tab_widget.addTab(memory_tab, "Pamięć")

        layout.addWidget(self.tab_widget)

        # Polecenie
        self.command_preview = QTextEdit()
        self.command_preview.setReadOnly(True)
        self.command_preview.setMinimumHeight(100)
        layout.addWidget(QLabel("Pełne polecenie:"))
        layout.addWidget(self.command_preview)

        # Przyciski
        button_layout = QHBoxLayout()
        self.ok_button = QPushButton("Dodaj zadanie")
        self.cancel_button = QPushButton("Anuluj")
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)

        # Połączenia
        self.c4d_file_btn.clicked.connect(self.browse_c4d_file)
        self.image_output_btn.clicked.connect(self.browse_image_output)
        self.multipass_output_btn.clicked.connect(self.browse_multipass_output)
        self.log_file_btn.clicked.connect(self.browse_log_file)
        self.use_file_settings.stateChanged.connect(self.on_use_file_settings_changed)

        # Połączenia dla przycisków OK i Cancel
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

        # Połączenia dla aktualizacji podglądu
        self.name_edit.textChanged.connect(self.update_command_preview)
        self.c4d_file_edit.textChanged.connect(self.update_command_preview)
        self.c4d_version_combo.currentTextChanged.connect(self.update_command_preview)
        self.frames_edit.textChanged.connect(self.update_command_preview)
        self.image_output_edit.textChanged.connect(self.update_command_preview)
        self.multipass_output_edit.textChanged.connect(self.update_command_preview)
        self.threads_spin.valueChanged.connect(self.update_command_preview)
        self.use_gpu.stateChanged.connect(self.update_command_preview)
        self.no_gui.stateChanged.connect(self.update_command_preview)
        self.batch_mode.stateChanged.connect(self.update_command_preview)
        self.shutdown.stateChanged.connect(self.update_command_preview)
        self.quit.stateChanged.connect(self.update_command_preview)
        self.debug_mode.stateChanged.connect(self.update_command_preview)
        self.show_console.stateChanged.connect(self.update_command_preview)
        self.log_file_edit.textChanged.connect(self.update_command_preview)
        self.verbose.stateChanged.connect(self.update_command_preview)
        self.memory_limit.valueChanged.connect(self.update_command_preview)
        self.priority_combo.currentTextChanged.connect(self.update_command_preview)

    def apply_styles(self):
        """Aplikuje style do przycisków"""
        self.c4d_file_btn.setStyleSheet(BUTTON_STYLES["default"])
        self.image_output_btn.setStyleSheet(BUTTON_STYLES["default"])
        self.multipass_output_btn.setStyleSheet(BUTTON_STYLES["default"])
        self.log_file_btn.setStyleSheet(BUTTON_STYLES["default"])
        self.ok_button.setStyleSheet(BUTTON_STYLES["primary"])
        self.cancel_button.setStyleSheet(BUTTON_STYLES["default"])

    def browse_c4d_file(self):
        """Otwiera dialog wyboru pliku C4D"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Wybierz plik Cinema 4D", "", "Cinema 4D Files (*.c4d)"
        )
        if file_path:
            self.c4d_file_edit.setText(file_path)

    def browse_image_output(self):
        """Otwiera dialog wyboru folderu dla obrazów"""
        folder_path = QFileDialog.getExistingDirectory(
            self, "Wybierz folder dla obrazów"
        )
        if folder_path:
            self.image_output_edit.setText(folder_path)

    def browse_multipass_output(self):
        """Otwiera dialog wyboru folderu dla multipass"""
        folder_path = QFileDialog.getExistingDirectory(
            self, "Wybierz folder dla multipass"
        )
        if folder_path:
            self.multipass_output_edit.setText(folder_path)

    def browse_log_file(self):
        """Otwiera dialog wyboru pliku logu"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Wybierz plik logu",
            "",
            "Log Files (*.log);;Text Files (*.txt);;All Files (*.*)",
        )
        if file_path:
            self.log_file_edit.setText(file_path)

    def on_use_file_settings_changed(self, state):
        """Obsługuje zmianę stanu checkboxa 'Użyj ustawień plików'"""
        is_checked = state == Qt.CheckState.Checked.value
        self.tab_widget.setEnabled(not is_checked)
        self.update_command_preview()

    def update_command_preview(self):
        """Aktualizuje podgląd polecenia na podstawie aktualnych ustawień"""
        c4d_exe = self.c4d_controller.c4d_installations[
            self.c4d_version_combo.currentText()
        ]
        command_parts = [f'"{c4d_exe}"']

        # Parametry renderowania
        if self.c4d_file_edit.text():
            command_parts.append(f'-render "{self.c4d_file_edit.text()}"')

        if not self.use_file_settings.isChecked():
            if self.frames_edit.text():
                command_parts.append(f"-frame {self.frames_edit.text()}")

            if self.image_output_edit.text():
                command_parts.append(f'-oimage "{self.image_output_edit.text()}"')

            if self.multipass_output_edit.text():
                command_parts.append(
                    f'-omultipass "{self.multipass_output_edit.text()}"'
                )

            command_parts.append(f"-threads {self.threads_spin.value()}")

            if self.use_gpu.isChecked():
                command_parts.append("-gpu")

            # Parametry trybu wsadowego
            if self.no_gui.isChecked():
                command_parts.append("cmd-nogui")
            if self.batch_mode.isChecked():
                command_parts.append("-batch")
            if self.shutdown.isChecked():
                command_parts.append("-shutdown")
            if self.quit.isChecked():
                command_parts.append("-quit")

            # Parametry debugowania
            if self.debug_mode.isChecked():
                command_parts.append("cmd-debug")
            if self.show_console.isChecked():
                command_parts.append("-console")
            if self.log_file_edit.text():
                command_parts.append(f'-log "{self.log_file_edit.text()}"')
            if self.verbose.isChecked():
                command_parts.append("-verbose")

            # Parametry pamięci
            command_parts.append(f"cmd-memory {self.memory_limit.value()}")
            command_parts.append(f"-priority {self.priority_combo.currentText()}")

        self.command_preview.setText(" ".join(command_parts))

    def get_task(self) -> RenderTask:
        """Tworzy i zwraca nowe zadanie renderowania"""
        # Walidacja wymaganych pól
        if not self.name_edit.text().strip():
            raise ValueError("Nazwa zadania jest wymagana")
        if not self.c4d_file_edit.text().strip():
            raise ValueError("Plik C4D jest wymagany")
        # Jeśli NIE jest zaznaczone 'Użyj ustawień plików', wymagaj ścieżki wyjściowej
        if not self.use_file_settings.isChecked():
            if not self.image_output_edit.text().strip():
                raise ValueError("Ścieżka wyjściowa obrazów jest wymagana")

        # Parsowanie zakresu klatek
        frames = self.frames_edit.text().strip()
        start_frame = None
        end_frame = None
        if frames:
            if "-" in frames:
                start_frame, end_frame = map(int, frames.split("-"))
            else:
                start_frame = end_frame = int(frames)

        # Przygotowanie ustawień renderowania
        render_settings = {
            "threads": self.threads_spin.value(),
            "use_gpu": self.use_gpu.isChecked(),
            "no_gui": self.no_gui.isChecked(),
            "batch_mode": self.batch_mode.isChecked(),
            "shutdown": self.shutdown.isChecked(),
            "quit": self.quit.isChecked(),
            "debug_mode": self.debug_mode.isChecked(),
            "show_console": self.show_console.isChecked(),
            "log_file": self.log_file_edit.text().strip(),
            "verbose": self.verbose.isChecked(),
            "memory_limit": self.memory_limit.value(),
            "priority": self.priority_combo.currentText(),
        }

        # Tworzenie zadania
        task = RenderTask(
            id=str(uuid.uuid4()),
            name=self.name_edit.text().strip(),
            c4d_file_path=self.c4d_file_edit.text().strip(),
            output_folder=(
                self.image_output_edit.text().strip()
                if not self.use_file_settings.isChecked()
                else ""
            ),
            cinema4d_version=self.c4d_version_combo.currentText(),
            start_frame=start_frame,
            end_frame=end_frame,
            render_settings=render_settings,
        )

        return task
