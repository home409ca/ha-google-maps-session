# Historia zmian

## 0.2.0

- Zastąpienie Xvfb i x11vnc jednym serwerem Xtigervnc (TigerVNC), który tworzy ekran i obsługuje VNC.
- Sprawdzenie powitania protokołu RFB przy starcie zamiast samego otwarcia portu TCP.
- Diagnostyka rozróżnia brak połączenia TCP od braku odpowiedzi na otwartym połączeniu.
- Profil Chromium i dane logowania zachowane w dotychczasowym katalogu.

## 0.1.3

- Serwer VNC używa jawnie adresu IPv4 127.0.0.1 zgodnego z adresem mostu WebSocket.
- Wyłączone mechanizmy X11 SHM i DAMAGE w serwerze VNC dla zgodności z kontenerem.
- Oczekiwanie na start ekranu i portu VNC zamiast samego stałego opóźnienia.
- Logi serwera ekranu, VNC, mostu WebSocket i panelu są widoczne w dzienniku dodatku; wyjście Chromium pozostaje ukryte.

## 0.1.2

- Jawne ustawienie adresu i portu połączenia noVNC zapobiega używaniu ustawień zapamiętanych z innych dodatków HA.
- Poprawna obsługa adresu panelu bez końcowego ukośnika.
- Przycisk „Sprawdź pulpit” sprawdza lokalny serwer VNC, most WebSocket i Chromium, a wyniki zapisuje też w logu.

## 0.1.1

- Pusty lub nieprawidłowy email nie zatrzymuje już pulpitu noVNC.
- Panel pokazuje brak wymaganej konfiguracji; synchronizacja czeka na jej zapisanie.
- Zapisany adres jest odczytywany ponownie przy każdej próbie synchronizacji.
- Log startowy informuje, czy zapisane ustawienie zostało przyjęte, bez ujawniania adresu.

## 0.1.0

- Pierwsza wersja eksperymentalna.
- Przeglądarka Chromium przez panel HA Ingress.
- Trwały profil Google i automatyczny eksport sesji.
- Moduł łączący z integracją pnbruckner/ha-google-maps 2.1.0.
- Repozytorium instalowalne przez adres GitHub w sklepie dodatków HA.
