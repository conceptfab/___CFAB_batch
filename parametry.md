Parametry uruchamiania Cinema 4D 2023 z CMD
Podstawowe parametry
cmdCinema4D.exe [parametry] [plik_projektu.c4d]
Parametry renderowania
cmd-render "ścieżka/do/pliku.c4d"          # renderuj projekt
-frame 1                                # renderuj konkretną klatkę  
-frame 1-100                           # renderuj zakres klatek
-frame 1,5,10                          # renderuj wybrane klatki
-oimage "ścieżka/output/obraz"         # ścieżka wyjściowa obrazów
-omultipass "ścieżka/output/multipass" # ścieżka multipass
-threads 8                             # liczba wątków CPU
-gpu                                   # używaj GPU do renderowania
Parametry trybu batch
cmd-nogui                                 # uruchom bez interfejsu
-batch                                 # tryb wsadowy
-shutdown                              # zamknij po zakończeniu
-quit                                  # wyjdź po renderowaniu
Parametry konfiguracji
cmd-prefs "ścieżka/do/preferencji"       # własne preferencje
-layout "nazwa_layoutu"                # konkretny layout interfejsu
-language en                           # język (en, de, fr, pl, etc.)
-user "ścieżka/folderu/użytkownika"   # folder użytkownika
Parametry debugowania
cmd-debug                                 # tryb debugowania
-console                               # pokaż konsolę
-log "ścieżka/do/logu.txt"            # zapisz log do pliku
-verbose                               # szczegółowe komunikaty
Parametry pamięci i wydajności
cmd-memory 4096                           # limit pamięci w MB
-priority high                         # priorytet procesu (low/normal/high)
-affinity 0x0F                        # przypisanie do rdzeni CPU
Parametry licencji
cmd-license "ścieżka/do/licencji"        # plik licencji
-server "adres_serwera_licencji"      # serwer licencji sieciowej
-port 5053                            # port serwera licencji
Parametry projektów Team Render
cmd-teamrender                            # uruchom jako Team Render Client
-server "192.168.1.100"               # adres Team Render Server
-renderqueue                           # uruchom kolejkę renderowania
Parametry specjalne
cmd-safe                                  # tryb bezpieczny (bez wtyczek)
-noplugins                            # wyłącz wszystkie wtyczki
-plugin "ścieżka/do/wtyczki"          # załaduj konkretną wtyczkę
-script "ścieżka/do/skryptu.py"       # wykonaj skrypt Python
Przykłady praktycznego użycia
Renderowanie wsadowe
Cinema4D.exe -render "C:\Projects\moj_projekt.c4d" -frame 1-100 -oimage "C:\Render\Output" 





Renderowanie konkretnej klatki
Cinema4D.exe -render "projekt.c4d" -frame 50 -threads 16 -quit
Uruchomienie z własną konfiguracją
Cinema4D.exe -prefs "C:\MyPrefs" -language pl -layout "My_Layout"
Team Render Client
Cinema4D.exe -teamrender -server "192.168.1.10" -nogui
Tryb debugowania
cmdCinema4D.exe -debug -console -log "C:\debug.log" -verbose
Zmienne środowiskowe
cmdset C4D_BROWSERURL="http://localhost"
set C4D_LANGUAGE=pl
set C4D_LICENSEPATH="C:\Licenses"
Cinema4D.exe
Kody wyjścia (Exit Codes)

0 - sukces
1 - błąd ogólny
2 - błąd renderowania
3 - błąd licencji
4 - błąd pliku projektu

Pliki konfiguracyjne
cmd# Można też używać plików .bat z parametrami
@echo off
Cinema4D.exe -render "%1" -nogui -shutdown -threads %NUMBER_OF_PROCESSORS%
Te parametry pozwalają na pełną automatyzację Cinema 4D z poziomu wiersza poleceń, szczególnie przydatne do renderowania wsadowego i integracji z pipeline'ami produkcyjnymi.




-render "ścieżka/do/pliku.c4d"          # renderuj projekt
-frame 1                                # renderuj konkretną klatkę  
-frame 1-100                           # renderuj zakres klatek
-frame 1,5,10                          # renderuj wybrane klatki
-oimage "ścieżka/output/obraz"         # ścieżka wyjściowa obrazów
-omultipass "ścieżka/output/multipass" # ścieżka multipass


-threads 8                             # liczba wątków CPU
-gpu                                   # używaj GPU do renderowania

Parametry trybu batch
cmd-nogui                                 # uruchom bez interfejsu
-batch                                 # tryb wsadowy
-shutdown                              # zamknij po zakończeniu
-quit                                  # wyjdź po renderowaniu


Parametry debugowania
cmd-debug                                 # tryb debugowania
-console                               # pokaż konsolę
-log "ścieżka/do/logu.txt"            # zapisz log do pliku
-verbose
                               # szczegółowe komunikaty
Parametry pamięci i wydajności
cmd-memory 4096                           # limit pamięci w MB
-priority high 


"C:\software\MAXON\Cinema 4D 2023_DEV\Commandline.exe" -render "C:\_cloud\Untitled 1.c4d" -verbose -console


  "status": "pending",