# Google Maps Session — repozytorium dodatków HA

Przeglądarka Google w panelu Home Assistant oraz automatyczne przekazywanie sesji do integracji [pnbruckner/ha-google-maps](https://github.com/pnbruckner/ha-google-maps).

## Wgranie na GitHub

1. Utwórz własne, publiczne repozytorium GitHub, np. `ha-google-maps-session`.
2. Rozpakuj paczkę na komputerze. W GitHub wybierz **Add file → Upload files** i przeciągnij zawartość rozpakowanego folderu, w tym folder `google_maps_session` i plik `repository.yaml`. Zatwierdź przez **Commit changes**. Nie wgrywaj samego ZIP-a.
3. Sprawdź, czy `repository.yaml` jest bezpośrednio w głównym katalogu repozytorium, obok folderu `google_maps_session`. Bez dodatkowego folderu opakowującego.

Oczekiwany układ:

```text
repository.yaml
README.md
LICENSE
google_maps_session/
  config.yaml
  Dockerfile
  README.md
  DOCS.md
  CHANGELOG.md
  nginx.conf
  app/
  bridge/
tests/
```

Adresu Twojego repozytorium nie trzeba wpisywać do plików pakietu. Repozytorium nie zawiera gotowych danych logowania; adres konta Google podajesz dopiero w konfiguracji dodatku w HA.

## Instalacja w Home Assistant

1. W HA otwórz **Ustawienia → Dodatki / Aplikacje → Sklep → menu ⋮ → Repozytoria**.
2. Wklej adres swojego repozytorium GitHub i kliknij **Dodaj**.
3. Odśwież sklep i zainstaluj **Google Maps Session** z sekcji tego repozytorium.
4. Ustaw swój adres **email** w konfiguracji dodatku i uruchom dodatek.
5. Zrestartuj **Home Assistant Core**, następnie w **Urządzenia i usługi → Dodaj integrację** dodaj **Google Maps Session Bridge**.
6. Otwórz panel dodatku, zaloguj właściwe konto Google i naciśnij **Przekaż sesję teraz**.

Wcześniej zainstaluj przez HACS integrację **pnbruckner/ha-google-maps 2.1.0**. Wymagany HA z Supervisorem, Core 2026.7 lub nowszy oraz amd64 lub aarch64. Szczegóły konfiguracji, ograniczenia i rozwiązywanie problemów: [dokumentacja dodatku](google_maps_session/DOCS.md).

Nie trzeba ręcznie kopiować dodatku do `/addons`, uruchamiać GitHub Actions ani publikować obrazu Docker. HA buduje obraz ze źródeł przy instalacji.

## Status

Wersja **0.1.0 — eksperymentalna**. Przeszło 10 testów offline oraz kontrola składni i struktury paczki. Nie wykonano jeszcze budowy Docker ani testu logowania Google na działającym HA. Google może wymagać ponownego zatwierdzenia logowania; dodatek nie omija jego zabezpieczeń.

Repozytorium przygotowano zgodnie z [układem repozytoriów dodatków HA](https://contributors.home-assistant.io/apps/guides/repository/).
