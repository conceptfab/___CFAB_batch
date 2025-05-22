# Cinema 4D Batch Renderer

Aplikacja do zarządzania kolejką zadań renderingu w Cinema 4D.

## Funkcjonalności

- Zarządzanie kolejką zadań renderingu
- Automatyczne wykrywanie zainstalowanych wersji Cinema 4D
- Monitorowanie zasobów systemowych
- Interfejs graficzny z tabelą zadań i logami
- Walidacja projektów przed renderingiem

## Wymagania

- Python 3.8+
- Cinema 4D (dowolna wersja)
- Windows 10/11

## Instalacja

1. Sklonuj repozytorium
2. Zainstaluj wymagane pakiety:
   ```
   pip install -r requirements.txt
   ```

## Uruchomienie

```
python main.py
```

## Struktura projektu

```
cinema4d_batch_renderer/
├── main.py
├── gui/
│   ├── main_window.py
│   └── task_dialog.py
├── core/
│   ├── queue_manager.py
│   └── cinema4d_controller.py
├── utils/
│   ├── logger.py
│   └── resource_monitor.py
├── models/
│   └── task.py
└── resources/
    └── icons/
```

## Licencja

MIT
