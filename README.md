# Google Maps Session

Przeglądarka Google w panelu Home Assistant i moduł **Google Maps Session Bridge** przekazujący sesję do integracji [pnbruckner/ha-google-maps](https://github.com/pnbruckner/ha-google-maps).

Repozytorium: https://github.com/home409ca/ha-google-maps-session

Zawiera dwa współpracujące elementy:

- **Google Maps Session** — dodatek instalowany ze sklepu dodatków HA. Uruchamia przeglądarkę, zachowuje sesję i eksportuje ciasteczka.
- **Google Maps Session Bridge** — integracja instalowana przez HACS. Rejestruje w HA akcję przekazania ciasteczek do integracji pnbrucknera.

## Wgranie paczki na GitHub

Rozpakuj ZIP i wgraj jego zawartość do głównego katalogu repozytorium `home409ca/ha-google-maps-session`, zachowując poniższy układ. Zatwierdź zmiany. Nie dodawaj zewnętrznego folderu opakowującego ani samego ZIP-a.

```text
hacs.json
repository.yaml
README.md
LICENSE
custom_components/
  google_maps_session_bridge/
    __init__.py
    config_flow.py
    manifest.json
    sync.py
    services.yaml
    strings.json
    translations/
    brand/icon.png
google_maps_session/
  config.yaml
  Dockerfile
  app/
  bridge/
  DOCS.md
tests/
```

W ustawieniach GitHub pozostaw repozytorium publiczne, włącz **Issues**, dodaj opis oraz tematy `home-assistant`, `hacs`, `google-maps`. Proponowany opis: „Google Maps login session add-on and HACS bridge for Home Assistant”. Plik manifestu wskazuje właściciela `@home409ca`, dokumentację tego repozytorium i jego zgłoszenia błędów.

## Instalacja modulu Bridge przez HACS

1. Wcześniej zainstaluj przez HACS integrację **pnbruckner/ha-google-maps 2.1.0**. Bridge wymaga jej kodu; wbudowana integracja Google Maps w HA nie wystarczy.
2. W HA otwórz **HACS → menu ⋮ → Repozytoria niestandardowe**.
3. Wpisz **https://github.com/home409ca/ha-google-maps-session**. Użyj adresu całego repozytorium, bez `/tree/main/...`.
4. Wybierz kategorię **Integracja / Integration**, następnie **Dodaj**.
5. Wyszukaj w HACS **Google Maps Session Bridge**, otwórz i wybierz pobranie / instalację.
6. Uruchom ponownie **Home Assistant Core**, po czym odśwież stronę HA w przeglądarce.
7. Przejdź do **Ustawienia → Urządzenia i usługi → Dodaj integrację → Google Maps Session Bridge** i zatwierdź.
8. Wróć do działającego dodatku Google Maps Session i kliknij **Przekaż sesję teraz**.

Jeśli Bridge był już dodany w „Urządzenia i usługi”, nie trzeba dodawać go drugi raz. Po pobraniu plików przez HACS wystarczy restart Core. HACS pobiera pliki, a ekran „Urządzenia i usługi” uruchamia integrację — potrzebne są oba etapy przy pierwszej instalacji.

Nie trzeba publikować GitHub Release: HACS może pobierać domyślną gałąź repozytorium. Paczka ma `hacs.json`, manifest, tłumaczenia i lokalną ikonę. Nie jest zgłoszona do domyślnego katalogu HACS; dodajesz ją jako repozytorium niestandardowe.

## Instalacja dodatku z przeglądarką

Jeśli dodatek już działa i jesteś zalogowany, zachowaj istniejącą instalację oraz profil. Wersja **0.2.1** dodatku zachowuje pliki Bridge zarządzane przez HACS; starsze wersje mogły je nadpisywać przy starcie. Zaktualizuj istniejący dodatek, aby kolejne jego uruchomienia zachowywały wersję Bridge z HACS.

Przy pierwszej instalacji:

1. Otwórz **Ustawienia → Dodatki / Aplikacje → Sklep → menu ⋮ → Repozytoria**.
2. Dodaj adres **https://github.com/home409ca/ha-google-maps-session**.
3. Zainstaluj **Google Maps Session**, wpisz swój `email` w konfiguracji i uruchom.
4. Dodaj Bridge przez HACS według instrukcji powyżej.
5. Otwórz panel dodatku, zaloguj jedno konto zgodne z ustawionym adresem i kliknij **Przekaż sesję teraz**.

Dodatek buduje obraz na urządzeniu HA. Wymaga HA z Supervisorem, Core 2026.7 lub nowszego oraz procesora amd64 albo aarch64. Pełny opis pracy, danych i rozwiązywania problemów: [dokumentacja dodatku](google_maps_session/DOCS.md).

## Sprawdzenie i ograniczenia

Po dodaniu Bridge w **Narzędzia deweloperskie → Akcje** powinna być dostępna akcja `google_maps_session_bridge.sync`. Jej obecność potwierdza uruchomienie modułu. Przy nieudanym przekazaniu sesji sprawdź **Ustawienia → System → Dzienniki → Home Assistant Core** i wpisy `google_maps_session_bridge`.

Wersja **0.2.1 — eksperymentalna**. Testy offline i lokalna kontrola plików nie zastępują instalacji na działającym HA. W dotychczasowym teście użytkownika przeglądarka i logowanie Google działały; pełne przekazanie sesji po instalacji Bridge pozostaje do potwierdzenia. Google może zażądać ponownego logowania lub zatwierdzenia dostępu.

Układ pakietu oparto na [wymaganiach integracji HACS](https://www.hacs.xyz/docs/publish/integration/). Bridge jest adapterem do konkretnej wersji zewnętrznej integracji, więc jej przyszłe zmiany mogą wymagać aktualizacji.
