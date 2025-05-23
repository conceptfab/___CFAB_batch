Problemy wydajnościowe w Cinema 4D Batch Renderer
🚨 Krytyczne problemy wydajnościowe
1. Blokowanie głównego wątku UI
Plik: utils/resource_monitor.py, funkcja get_system_resources()
python# PROBLEM: interval=1 blokuje wątek UI na 1 sekundę!
return {
    "cpu": psutil.cpu_percent(interval=1),  # ← To blokuje UI!
    "memory": psutil.virtual_memory().percent,
    "disk": psutil.disk_usage(disk_path).percent,
}
Rozwiązanie:
pythondef get_system_resources(self) -> Dict[str, float]:
    """Zwraca aktualny stan zasobów systemowych"""
    try:
        disk_path = os.path.abspath(os.sep)
        
        return {
            "cpu": psutil.cpu_percent(interval=0),  # Non-blocking!
            "memory": psutil.virtual_memory().percent,
            "disk": psutil.disk_usage(disk_path).percent,
        }
    except Exception as e:
        self.logger.error(f"Błąd odczytu zasobów systemowych: {str(e)}")
        return {"cpu": 0, "memory": 0, "disk": 0}
2. Zbyt częste aktualizacje UI
Plik: gui/main_window.py, metoda setup_timer()
python# PROBLEM: Aktualizacja co sekundę jest zbyt częsta
self.update_timer.start(1000)  # ← Co sekundę!
Rozwiązanie:
pythondef setup_timer(self):
    """Konfiguruje timer dla aktualizacji UI"""
    self.update_timer = QTimer()
    self.update_timer.timeout.connect(self.update_ui)
    self.update_timer.start(3000)  # Aktualizacja co 3 sekundy
3. Niepotrzebne przebudowywanie tabeli
Plik: gui/main_window.py, metoda update_tasks_table()
python# PROBLEM: Zawsze przebudowuje całą tabelę
def update_tasks_table(self):
    """Aktualizuje tabelę zadań"""
    self.tasks_table.setRowCount(len(self.queue_manager.tasks))
    
    for row, task in enumerate(self.queue_manager.tasks):
        # Zawsze tworzy nowe QTableWidgetItem - niepotrzebnie!
        self.tasks_table.setItem(row, 0, QTableWidgetItem(task.name))
        # ... reszta kolumn
Rozwiązanie:
pythondef update_tasks_table(self):
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
4. Brakujące asynchroniczne operacje
Plik: gui/main_window.py - dodaj asynchroniczny monitoring zasobów
pythonfrom PyQt6.QtCore import QThread, pyqtSignal

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

# W klasie MainWindow:
def setup_resource_monitoring(self):
    """Konfiguruje asynchroniczny monitoring zasobów"""
    self.resource_thread = ResourceMonitorThread()
    self.resource_thread.resources_updated.connect(self.update_resources)
    self.resource_thread.start()

def update_resources(self, resources: dict):
    """Aktualizuje wyświetlanie zasobów (wywoływane przez sygnał)"""
    self.cpu_label.setText(f"CPU: {resources['cpu']:.1f}%")
    self.memory_label.setText(f"RAM: {resources['memory']:.1f}%")
    self.disk_label.setText(f"Dysk: {resources['disk']:.1f}%")
5. Optymalizacja widżetu statusu workerów
Plik: gui/worker_status_widget.py
pythondef update_workers(self, workers: list[RenderWorker]):
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

def _update_worker_widget(self, widget: QWidget, worker: RenderWorker):
    """Aktualizuje istniejący widżet workera"""
    widget.worker_label.setText(f"Worker {worker.worker_id}:")
    
    if worker.is_busy and worker.current_task:
        text = f"Renderuje: {worker.current_task.name}"
        color = "#10B981"  # Zielony
    else:
        text = "Bezczynny"
        color = "#9CA3AF"  # Szary
    
    widget.status_label.setText(text)
    widget.status_label.setStyleSheet(f"color: {color};")
6. Uproszczenie timera w głównym oknie
Plik: gui/main_window.py
pythondef setup_timer(self):
    """Konfiguruje timer dla aktualizacji UI"""
    # Rozdziel timery na różne częstotliwości
    
    # Timer dla tabeli zadań (rzadziej)
    self.tasks_timer = QTimer()
    self.tasks_timer.timeout.connect(self.update_tasks_table)
    self.tasks_timer.start(5000)  # Co 5 sekund
    
    # Timer dla statusu workerów (częściej)
    self.workers_timer = QTimer()
    self.workers_timer.timeout.connect(self.update_worker_status)
    self.workers_timer.start(2000)  # Co 2 sekundy

def update_ui(self):
    """Lekka aktualizacja UI - usuń ciężkie operacje"""
    # Usuń aktualizację tabeli i zasobów - mają własne timery
    pass

def update_worker_status(self):
    """Aktualizuje tylko status workerów"""
    workers = self.queue_manager.get_worker_status()
    self.worker_status_widget.update_workers(workers)
📋 Pełna lista zmian do wprowadzenia

Zmień psutil.cpu_percent(interval=1) na interval=0 w resource_monitor.py
Zwiększ interwał timera z 1s na 3-5s w main_window.py
Dodaj asynchroniczne monitorowanie zasobów używając QThread
Zoptymalizuj aktualizację tabeli - aktualizuj tylko zmienione komórki
Rozdziel timery na różne częstotliwości według ważności
Popraw widżet statusu workerów - nie przebudowuj za każdym razem

Te zmiany powinny znacząco poprawić responsywność UI i zmniejszyć zużycie CPU przez aplikację.