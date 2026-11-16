# Google Maps Session

Dodatek do Home Assistant z przeglądarką dostępną w panelu HA. Pozwala zalogować się do Google i automatycznie przekazuje sesję do niestandardowej integracji `pnbruckner/ha-google-maps`.

- Logowanie i weryfikacja Google w oknie przeglądarki w panelu HA.
- Zachowanie profilu po restarcie.
- Automatyczna synchronizacja ciasteczek i przeładowanie konta integracji.
- Powiadomienie w HA, gdy sesji nie można przekazać.

Wymaga Home Assistant z Supervisorem, procesora amd64 lub aarch64 i integracji pnbrucknera 2.1.0. Moduł łączący jest instalowany przy pierwszym starcie dodatku; następnie trzeba zrestartować HA i dodać integrację **Google Maps Session Bridge**.

**Wersja eksperymentalna:** testy offline przeszły, ale budowa kontenera, panel i prawdziwe logowanie Google nie zostały jeszcze przetestowane pod HA.

Pełna instrukcja znajduje się w zakładce **Dokumentacja** dodatku lub w pliku [DOCS.md](DOCS.md).
