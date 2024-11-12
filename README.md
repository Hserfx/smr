
# SMR

SMR to aplikacja napisana w Pythonie, która integruje się z API GoPOS, umożliwiając generowanie szczegółowych raportów sprzedażowych oraz raportów podatkowych na podstawie zamówień i faktur. Skrypt automatycznie pobiera dane z systemu, segreguje je oraz przetwarza na zdefiniowane formaty raportów.

## Funkcje aplikacji

- **Autoryzacja z GoPOS API**: Pobiera token dostępu potrzebny do komunikacji z GoPOS API.
- **Pobieranie zamówień**: Zbiera informacje o zamówieniach w zadanym zakresie dat.
- **Pobieranie faktur**: Pozyskuje szczegóły faktur powiązanych z zamówieniami.
- **Generowanie raportów sprzedażowych i podatkowych**: Tworzy raporty w formacie tekstowym zawierające szczegóły sprzedaży, podatków oraz metod płatności.

## Wymagania

- Python 3.7+
- Biblioteki wymienione w `requirements.txt`, które możesz zainstalować za pomocą:
  ```bash
  pip install -r requirements.txt
  ```

## Użycie

Przed uruchomieniem aplikacji upewnij się, że plik `.env` zawiera dane dostępowe do GoPOS API.

### Przykłady wywołań funkcji

#### `get_token(url, creds, **kwargs)`
- Wysyła żądanie, aby uzyskać token dostępu do API. 
- **Parametry**:
  - `url`: URL do endpointu tokenu w GoPOS API.
  - `creds`: Dane logowania w formacie słownika.

#### `get_orders(id, headers)`
- Pobiera zamówienia o statusie "CLOSED" w zadanym zakresie dat.
- **Parametry**:
  - `id`: Identyfikator użytkownika lub organizacji.
  - `headers`: Nagłówki HTTP zawierające token autoryzacyjny.

#### `get_invoice(id, invoice_no, headers)`
- Pozyskuje dane o fakturach potwierdzonych dla danego numeru zamówienia.
- **Parametry**:
  - `id`: Identyfikator użytkownika lub organizacji.
  - `invoice_no`: Numer faktury.
  - `headers`: Nagłówki HTTP zawierające token autoryzacyjny.

#### `count_taxes(orders, payment_method)`
- Przetwarza zamówienia, obliczając kwoty netto, VAT oraz brutto według metody płatności.
- **Parametry**:
  - `orders`: Lista zamówień.
  - `payment_method`: Metoda płatności, np. "Gotówka" lub "Karta".

#### `invoice_report(order, prefix)`
- Tworzy raport w formacie tekstowym dla faktur, zawierający szczegóły podatkowe i płatności.
- **Parametry**:
  - `order`: Dane o zamówieniu.
  - `prefix`: Prefiks dołączany do numeru raportu.

### Przykładowe uruchomienie
Skrypt można uruchomić bezpośrednio, aby wygenerować raporty sprzedaży i podatków:
```bash
python main.py
```

---

## Struktura projektu

- **`main.py`**: Główne funkcje skryptu odpowiedzialne za komunikację z API i generowanie raportów.
- **`utils.py`** (jeśli istnieje): Funkcje pomocnicze do zarządzania danymi, jak formatowanie raportów czy zapisywanie plików.

## Uwagi

Skrypt został stworzony do pracy w środowisku GoPOS i wymaga skonfigurowanych zmiennych środowiskowych w `.env`.
