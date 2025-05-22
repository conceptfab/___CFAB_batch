Chce zbudować aplikację w pythonie opartą o UI PyQT6, która będzie zarządzała renderingiem wsadowym w Cinema 4D. Do komunikacji w z Cinema 4d ma używać linii komend i maksymalnie wykorzystywać tą możliwość.
Założenia:

- czytelny UI
- pełna kontrola na kolejką zadań, nowe zadanie ma być kontynuowane po zakończeniu poprzedniego
- w wypadku błedów jednego zadania, program ma umożliwiać realizację kolejnego w kolejce
- logowanie komunikatów o błędach, logowanie informacji czasie renderingu
- każde zadanie może wykorzystywać inną wersję Cinema 4D
- weryfikacja brakujących tekstur, pluginów w projekcie/pliku
- zadania są realizowane w oparciu o ustawienia w pliku, ale także możliwe jest ustawienia w każdym zadaniu indywidualnego zakresu renderingu (klatki), osobnego folderu zapisu plików
- monitorowanie czy pliki zostały zapisane w docelowym folderze, wysyłanie raportów mailem z miniaturkami plików i czasem renderingu
- jeśli to możliwe, kontrola zasobów systemowych w celu optymalizacji procesu renderingu
