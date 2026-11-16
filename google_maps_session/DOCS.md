# Google Maps Session — dodatek do Home Assistant

Wersja 0.1.0, eksperymentalna. Dodatek instalowany z repozytorium GitHub dodanego do sklepu HA. Obraz buduje się na urządzeniu HA; nie wymaga osobnego rejestru obrazów ani GitHub Actions.

Logujesz się do Google w przeglądarce widocznej w panelu HA. Dodatek zachowuje jej profil i przekazuje ciasteczka do integracji pnbruckner/ha-google-maps. Nie trzeba pobierać ani wgrywać plików ciasteczek ręcznie. Hasło wpisujesz na stronie Google, nie w konfiguracji dodatku.

## Wymagania

- Home Assistant OS albo instalacja z działającym Supervisorem i obsługą lokalnych dodatków. Sam HA Container nie ma sklepu dodatków.
- HA Core 2026.7 lub nowszy.
- Zainstalowana przez HACS niestandardowa integracja [pnbruckner/ha-google-maps](https://github.com/pnbruckner/ha-google-maps), wersja 2.1.0. Nie chodzi o wbudowaną integrację HA.
- Procesor amd64 (np. mini PC) lub aarch64 (np. Raspberry Pi z 64-bitowym HA).
- Dostęp do internetu podczas budowy obrazu oraz pracy dodatku. Chromium potrzebuje zauważalnie więcej pamięci niż sama integracja; przewidź około 1 GB wolnego RAM, na słabszych urządzeniach więcej.

Adapter opracowano na podstawie kodu integracji 2.1.0, commit `ae85b249b354c25c2994cd1458231039e1dc977f`. Nowsze wydania mogą wymagać dostosowania. Nie jest to oficjalny dodatek Google ani autora integracji.

## Pierwsza instalacja

1. Zainstaluj integrację pnbruckner/ha-google-maps przez HACS i uruchom ponownie HA, jeśli HACS tego wymaga. Nie musisz jeszcze dodawać w niej konta.
2. W HA otwórz **Ustawienia → Dodatki / Aplikacje → Sklep → menu ⋮ → Repozytoria**. Wklej adres repozytorium GitHub zawierającego ten dodatek i kliknij **Dodaj**. Użyj adresu całego repozytorium, nie pliku, podfolderu ani paczki ZIP.
3. Zamknij okno repozytoriów i odśwież sklep. W sekcji **Google Maps Session — dodatki Home Assistant** znajdź **Google Maps Session**. Jeżeli sekcji nie widać, wybierz sprawdzenie aktualizacji sklepu i sprawdź, czy w głównym katalogu repozytorium jest plik `repository.yaml`.
4. Otwórz **Google Maps Session → Zainstaluj**. Obraz buduje się na urządzeniu HA, więc pierwsza instalacja może potrwać kilka–kilkanaście minut.
5. W konfiguracji dodatku ustaw **email** na adres konta Google, którego będziesz używać. Pozostałe opcje możesz zostawić domyślne. Zapisz i uruchom dodatek.
6. Pierwszy start kopiuje mały moduł łączący do `/config/custom_components/google_maps_session_bridge` (w kontenerze dodatku ten sam katalog to `/homeassistant/custom_components/...`). **Uruchom ponownie Home Assistant Core**.
7. Przejdź do **Ustawienia → Urządzenia i usługi → Dodaj integrację**, wyszukaj **Google Maps Session Bridge** i zatwierdź. Jeśli nie widać nazwy, odśwież przeglądarkę po restarcie HA.
8. Otwórz interfejs dodatku **Google Maps Session**. Możesz włączyć pokazywanie go na pasku bocznym. Zaloguj się w widocznym oknie Chromium i potwierdź logowanie na telefonie, jeśli Google o to poprosi.
9. **Użyj tylko jednego konta Google w tej przeglądarce: dokładnie tego, które wpisałeś w konfiguracji.** Po zalogowaniu otwórz Mapy Google i naciśnij **Przekaż sesję teraz**. Jeśli potrzebujesz, wpisz `https://www.google.com/maps` w pasku adresu widocznej przeglądarki.
10. Oczekiwany komunikat to **Sesja przekazana do integracji Google Maps**. Istniejące konto o tym adresie zostanie zaktualizowane. Jeśli konta jeszcze nie ma, moduł utworzy je przez standardowy proces konfiguracji integracji. Encje znajdziesz w integracji Google Maps; ich nazwy zależą od udostępnionych osób.

Po zakończeniu możesz zamknąć panel. **Nie wylogowuj konta Google.** Dodatek musi pozostać uruchomiony; profil przeglądarki jest zapisany w jego danych i przetrwa restart.

Przy automatycznym tworzeniu konta tracker samego konta jest wyłączony, limit dokładności wynosi 1000 m, a interwał lokalizacji 60 sekund. Te opcje zmienisz później w ustawieniach integracji Google Maps. Ustawienia istniejącego konta pozostają zachowane.

## Jak pracuje automatyzacja

- Co `sync_interval` sekund, domyślnie 300 (5 minut), odczytuje aktualne ciasteczka lokalnej przeglądarki.
- Przekazuje zmieniony komplet do modułu w HA. Dodatkowo raz na godzinę sprawdza sesję nawet przy niezmienionych ciasteczkach. Naciśnięcie przycisku wymusza próbę natychmiast.
- Moduł wykonuje rzeczywiste zapytanie do Google przez bibliotekę docelowej integracji. Jeśli sesja jest odrzucona, nie zastępuje nią dotychczasowej konfiguracji.
- Po poprawnej walidacji zapisuje ciasteczka pod nową nazwą i przeładowuje odpowiednie konto. Nowa nazwa zapobiega nadpisaniu świeżej sesji przez poprzednie ciasteczka trzymane w pamięci integracji. Nie edytuje bezpośrednio plików rejestru `.storage`.
- Co `refresh_minutes` minut odświeża otwartą kartę Map Google, domyślnie co 30 minut. Nie odświeża stron logowania Google. Wartość 0 wyłącza odświeżanie. Nie gwarantuje ono przedłużenia sesji.
- Brak zalogowania lub błąd przekazania powoduje powiadomienie w HA. Po udanej synchronizacji powiadomienie jest usuwane.

To nie jest mechanizm automatycznego wpisywania hasła ani obchodzenia weryfikacji Google. Google może odrzucić logowanie z takiej przeglądarki, zakończyć sesję albo wymagać nowego potwierdzenia. Tych sytuacji nie udało się tu sprawdzić na działającym koncie; w razie wystąpienia mogą wymagać poprawki dodatku lub ręcznego ponownego logowania w panelu. Dodatek obsługuje jedno konto na instalację. Adres w konfiguracji określa konto docelowe, ale nie jest automatycznie porównywany z tożsamością zalogowaną w Google — dlatego wymóg jednego właściwego konta jest istotny.

## Gdy coś nie działa

**Nie mogę zsynchronizować sesji:** upewnij się, że po pierwszym starcie dodatku zrestartowałeś HA i dodałeś integrację Google Maps Session Bridge. Sprawdź, czy używasz niestandardowej integracji pnbrucknera 2.1.0, czy konto nie jest wyłączone i czy nie ma zduplikowanych wpisów. Ponów próbę. Błąd sieci nie musi oznaczać wygaśnięcia sesji.

**Google wymaga logowania:** otwórz panel dodatku, zaloguj właściwe konto i naciśnij przycisk przekazania sesji. Nie trzeba eksportować pliku.

**Google nie pozwala się zalogować:** sprawdź komunikat widoczny w przeglądarce. Nie ma tu obietnicy obejścia blokad Google. Nie resetuj wszystkich swoich sesji ani ustawień bezpieczeństwa konta jako pierwszego kroku.

**Czarny ekran albo panel się nie otwiera:** odczekaj około 30 sekund, sprawdź log dodatku, uruchom go ponownie i sprawdź wolną pamięć. Przeglądarka i serwer pulpitu nie są wystawione na osobnych portach; panel działa przez dostęp HA. Niestandardowa sieć Supervisora może wymagać zmiany adresu dozwolonego w `nginx.conf` (standardowo 172.30.32.2).

**Sesja działa, ale nie ma lokalizacji:** sprawdź w Google Maps, czy odpowiednie osoby udostępniają lokalizację temu kontu. Samo poprawne logowanie nie tworzy udostępnień.

Log modułu w HA zawiera typ błędu, bez treści ciasteczek. Nie wysyłaj nikomu plików ciasteczek, profilu przeglądarki ani kopii zapasowej zawierającej te dane.

## Dane i uprawnienia

Panel jest dostępny przez HA Ingress, dla administratora. VNC, połączenie do przeglądarki i serwer pomocniczy słuchają tylko lokalnie w kontenerze. Dodatek nie publikuje portów hosta. Chromium działa jako osobny użytkownik; jego własny sandbox jest wyłączony ze względu na uruchomienie wewnątrz kontenera dodatku.

Dodatek ma dostęp do API HA z uprawnieniami administracyjnymi, zapisu katalogu konfiguracji HA (instalacja własnego modułu) i `/share` (przekazywanie ciasteczek). Nie wyłącza trybu ochrony dodatku. Profil znajduje się w prywatnych danych `/data/profile`, eksport w `/share/google_maps_session/cookies.txt`, a integracja zapisuje własny komplet ciasteczek w swoim zwykłym magazynie. Ciasteczka i profil umożliwiają dostęp do zalogowanej sesji. Najlepiej przeznaczyć do tego osobne konto Google, któremu zainteresowane osoby dobrowolnie udostępnią lokalizację. Backup zawiera sesję; traktuj go jak dane logowania. Backup jest wykonywany po zatrzymaniu dodatku, żeby zachować spójność profilu.

Przy usuwaniu: zatrzymaj dodatek, usuń integrację Bridge w HA i odinstaluj dodatek. Moduł w `custom_components/google_maps_session_bridge` oraz `/share/google_maps_session` usuń osobno, jeśli nie są już potrzebne. Zwykła integracja Google Maps i jej konfiguracja nie są automatycznie usuwane. Wylogowanie odpowiedniej sesji w koncie Google unieważni dostęp także po stronie integracji.

## Weryfikacja przed wydaniem

Przeprowadzono testy offline konwersji ciasteczek, ponowień po błędach, zachowania dotychczasowego wpisu po odrzuceniu sesji, nowej nazwy pliku przed przeładowaniem i sekwencji tworzenia konta. Przeprowadzono kontrolę składni plików Python, JSON, YAML i JavaScript panelu.

**Nie zbudowano obrazu Docker ani nie uruchomiono go pod Supervisorem, na amd64 lub aarch64. Nie wykonano prawdziwego logowania Google i testu end-to-end w HA.** W tym środowisku nie ma Dockera ani instancji HA. Wersja jest przygotowana do pierwszego testu instalacyjnego, nie ma potwierdzenia działania na Twoim urządzeniu.

Kod integracji źródłowej: https://github.com/pnbruckner/ha-google-maps

Konfiguracja dodatków HA: https://contributors.home-assistant.io/apps/reference/configuration/

Interfejs przeglądarki CDP: https://chromedevtools.github.io/devtools-protocol/tot/Storage/
