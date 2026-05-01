# Technical Specification – Accounting Application

**Version:** 1.1  
**Date:** May 1, 2026  
**Technology:** FastAPI, SQLAlchemy, SQLite, Jinja2

---

## 1. Yleiskuvaus

Kirjanpito-ohjelma on suomalainen finanssisovellus, joka hallinnoi kuluja ja tuloja useille kustannuspaikoille (asunnot, metsät, muut). Ohjelmalla voi:
- Tallentaa multi-line kuluja/tuloja kuiteilla (PDF/kuva)
- Tallentaa kilometrikuluja ajopäiväkirjariveinä
- Merkitä kulun tilaan `Ei kuittia`, jolloin puuttuvasta kuitista ei varoiteta
- Hallita kustannuspaikkoja ja kategorioita
- Luoda vuosiraportteja ALV-laskennalla
- Ladata vuosiraportin kaikki tositteet yhdistettynä yhdeksi PDF-tiedostoksi
- Jakaa multi-page PDF-kuitteja yksittäisiksi sivuiksi

---

## 2. Tietokanta-schema

### 2.1 Taulut

#### `cost_centers`
Kustannuspaikat (asunnot, metsät, muut).

| Sarake | Tyyppi | Kuvaus |
|--------|--------|--------|
| id | INTEGER PK | Tunniste |
| name | TEXT | Nimi (esim. "Pääasunto", "Metsä 1") |
| center_type | TEXT | Tyyppi: `apartment`, `forest`, `other` |
| vat_deductible | BOOLEAN | Onko ALV-vähennyskelpoinen |

#### `expense_categories`
Kululajit ja tulolajit.

| Sarake | Tyyppi | Kuvaus |
|--------|--------|--------|
| id | INTEGER PK | Tunniste |
| name | TEXT | Nimi (esim. "Siivous", "Korjaus") |
| category_type | TEXT | `expense` tai `income` |
| **UNIQUE** | (name, category_type) | Saman nimen eri tyypit OK |

#### `expenses`
Pääkulutapahtumat.

| Sarake | Tyyppi | Kuvaus |
|--------|--------|--------|
| id | INTEGER PK | Tunniste |
| cost_center_id | INTEGER FK | Viite cost_centers |
| date | DATE | Tapahtumainen päivä |
| description | TEXT | Yleinen kuvaus |
| reference | TEXT UNIQUE | Viite-numero muodossa YYYY-NNN |
| receipt_image_path | TEXT | Kuitti-tiedoston nimi |
| no_receipt | BOOLEAN | Tapahtuma on tarkoituksella ilman kuittia |
| entry_type | TEXT | `income` tai `expense` |

#### `expense_lines`
Rivit kunkin kulun sisällä (multi-line support).

| Sarake | Tyyppi | Kuvaus |
|--------|--------|--------|
| id | INTEGER PK | Tunniste |
| expense_id | INTEGER FK | Viite expenses (CASCADE DELETE) |
| category_id | INTEGER FK | Viite categories (nullable) |
| description | TEXT | Rivivivaisu |
| gross_amount | DECIMAL | Kokonaissumma €. |
| vat_rate | DECIMAL | ALV % (esim. 24.0) |
| vat_amount | DECIMAL | Laskettu ALV € |
| net_amount | DECIMAL | Nettosumma € |
| mileage_km | DECIMAL | Ajetut kilometrit, jos kyseessä kilometririvi |
| mileage_rate | DECIMAL | Km-korvaus euroina per km |
| vehicle | TEXT | Ajoneuvo, esim. oma auto |
| route_from | TEXT | Lähtöpaikka |
| route_to | TEXT | Kohde |
| sort_order | INTEGER | Rivin järjestys |

#### `apartment_year_settings`
Vuosittaiset asetukset asunnoille.

| Sarake | Tyyppi | Kuvaus |
|--------|--------|--------|
| id | INTEGER PK | Tunniste |
| cost_center_id | INTEGER FK | Asunnolle |
| year | INTEGER | Vuosi |
| maintenance_charge_net | DECIMAL | Hoitovastike netto |

---

## 3. REST API

### 3.1 Kulut (`/expenses`)

#### GET `/expenses/` – Lista kuluista
Parametrit:
- `cost_center_id` (int): Suodata kustannuspaikalle
- `year` (int): Vuoden mukaan

**Response:** 200 OK
```json
[
  {
    "id": 1,
    "reference": "2026-001",
    "date": "2026-04-15",
    "description": "Siivous",
    "entry_type": "expense",
    "total_gross": 120.00,
    "total_vat": 20.00,
    "total_net": 100.00,
    "category_names": ["Siivous"],
    "lines": [
      {
        "id": 1,
        "description": "Pyykinpesu",
        "gross_amount": 120.00,
        "vat_rate": 24.0
      }
    ]
  }
]
```

#### POST `/expenses/new` – Uusi kulu
**Form Data:**
- `cost_center_id` (int)
- `expense_date` (date)
- `description` (str)
- `entry_type` ("expense" | "income")
- `receipt` (file, optional)
- `no_receipt` (`"1"`, optional)
- `expense_mode` (`"standard" | "mileage"`)
- Line data (multi-value):
  - `line_category_id` (int, optional)
  - `line_description` (str)
  - `line_gross_amount` (decimal)
  - `line_vat_rate` (decimal)

Kilometrikulussa käytetään kenttiä:
- `line_route_from`
- `line_route_to`
- `line_vehicle`
- `line_mileage_km`
- `line_mileage_rate`

Kilometrikulun summa lasketaan kaavalla `mileage_km * mileage_rate`, ja ALV on `0`.

**Response:** 303 Redirect (Tapahtumapaikan listaan)

#### GET `/expenses/{id}/edit` – Muokkaa kulua
**Response:** 200 OK (HTML form)

#### POST `/expenses/{id}/edit` – Tallenna muokattu kulu
Samat parametrit kuin POST /new.

**Response:** 303 Redirect

#### Kuittikäytäntö
- Jos tapahtumalle on liitetty tiedosto, kuitti näytetään normaalisti.
- Jos `no_receipt = true`, käyttöliittymä näyttää tilan **Ei kuittia**.
- Jos tapahtuma on kulu eikä sillä ole kuittia eikä `no_receipt`-merkintää, vuosiraportti näyttää varoituksen.

#### POST `/expenses/{id}/delete` – Poista kulu
**Response:** 303 Redirect

---

### 3.2 Kustannuspaikat (`/cost_centers`)

#### GET `/cost_centers/` – Lista
**Response:** 200 OK (HTML)

#### POST `/cost_centers/new` – Uusi paikka
- `name` (str)
- `center_type` ("apartment" | "forest" | "other")
- `vat_deductible` (bool)

---

### 3.3 Kategoriat (`/categories`)

#### GET `/categories/` – Lista
#### POST `/categories/new` – Uusi kategoria
- `name` (str)
- `category_type` ("expense" | "income")

---

### 3.4 Raportit (`/reports`)

#### GET `/reports/yearly?cost_center_id={id}&year={year}` – Vuosiraportti
**Response:** 200 OK (HTML)

Näyttää:
1. **Yhteenveto kategorioittain** (collapsible summary)
2. Kategoriot joissa +/- toggle näyttää/piilottaa rivit
3. Varoitusosion kuluista, joilta puuttuu kuitti

**Data rakenne:**
```python
{
  "center": CostCenter,
  "year": 2026,
  "summary": {
    "income_rows": [{"category": str, "count": int, "net": decimal, ...}],
    "expense_rows": [...],
    "result_gross": decimal
  },
  "missing_receipts": [Expense, ...],
  "grouped": {
    "income": [
      {
        "category": str,
        "items": [(Expense, ExpenseLine), ...],
        "subtotal_net": decimal
      }
    ],
    "expense": [...]
  }
}
```

#### GET `/reports/yearly/csv?...` – CSV export
CSV-tiedosto joka sisältää rivin per expense_line.

#### GET `/reports/mileage?...` – Ajopäiväkirja
- Hakee valitun kustannuspaikan ja vuoden kilometririvit
- Näyttää päivämäärän, tunnuksen, tarkoituksen, reitin, auton, kilometrit ja korvauksen
- Soveltuu selaimesta tulostettavaksi ajopäiväkirjaksi

#### GET `/reports/yearly/receipts-pdf?...` – Yhdistetty tositteiden PDF
- Yhdistää valitun kustannuspaikan ja vuoden kaikki tositteet yhdeksi PDF:ksi
- PDF-kuitit lisätään sivu kerrallaan
- Kuittikuvat (JPG, PNG, WEBP) renderöidään A4-sivuille
- Jokaiselle sivulle lisätään teksti `Kuitin tunnus: YYYY-NNN`
- Puuttuvat tai rikkoutuneet tiedostot ohitetaan, jotta lataus ei kaadu koko aineistoon

---

## 4. Frontend

### 4.1 Sivut

| Sivu | Polku | Kuvaus |
|------|-------|--------|
| Lista | `/expenses/` | Tapahtumaluettelo |
| Uusi | `/expenses/new` | Uuden tapahtuman muoto |
| Muokkaa | `/expenses/{id}/edit` | Tapahtuman muokkaus |
| Kategoriat | `/categories/` | Kategorialuettelo |
| Raportit | `/reports/index` | Raportin valinta |
| Vuosiraportti | `/reports/yearly` | Vuosikatsaus |

### 4.2 JavaScript (`static/app.js`)

**Funktiot:**
- `updateTotals()` – Päivitä rivin ALV/summät realtime
- `addLine()` – Lisää uusi rivi
- `removeLine()` – Poista rivi
- Event delegation multi-line käsittelyyn

### 4.3 Collapsible kategoriat (yearly.html)

```html
<!-- Kategoriarivin klikkaus avaa/sulkee detail-rivit -->
<tr class="category-header" onclick="toggleDetails(this)">
  <td><span class="expand-icon">+</span></td>
  <td>Kategoria</td>
  ...
</tr>
<!-- Detail rows piilotettu oletuksena -->
<tr class="detail-row" style="display: none;">
  ...
</tr>
```

### 4.4 Kuitin tila käyttöliittymässä
- Tapahtumalomakkeella on valinta **Ei kuittia**
- Tapahtumalistalla kuittisarakkeessa näkyy joko kuitti, **Ei kuittia** tai varoitus **Puuttuu**
- Vuosiraportti näyttää varoituslistan vain niistä kuluista, joilta kuitti puuttuu ilman `Ei kuittia`-merkintää

### 4.5 Kilometrikulut käyttöliittymässä
- Tapahtumalistalla on erillinen nappi **Lisää kilometrikulu**
- Kilometrikulussa voidaan syöttää useita ajopäiväkirjarivejä samalle tapahtumalle, esimerkiksi meno- ja paluumatka
- Ajopäiväkirja on saatavilla raporttisivulta ja vuosiraportilta omalla painikkeellaan

---

## 5. Kuitti-käsittely

### 5.1 Tallennus (expenses.py)

```python
def _save_receipt(file):
    """Tallenna kuitti ilman pakkausta."""
    # Validoi tiedostotyyppi
  # Tallenna data/receipts/<db>/<year>/ hakemistoon UUID-nimillä
  # Palauta suhteellinen polku
```

### 5.2 Yhdistetty tositteiden PDF
- PDF-tiedostot yhdistetään suoraan uuteen PDF-dokumenttiin
- Kuvat asetetaan A4-sivulle kuvasuhde säilyttäen
- Jokaiselle sivulle lisätään kuitin tunnus näkyvänä leimana

### 5.3 Optimointi (split_pdf.py)

Erillinen **split_pdf.py** skripti:
```bash
python split_pdf.py input.pdf [output_dir] --dpi 85 --quality 20
```

Rasteroi multi-page PDF:t yksittäisiksi sivuiksi grayscale JPEG:nä (85 DPI, quality 20).

---

## 6. Viite-numerosysteemi

Format: `YYYY-NNN` (esim. `2026-001`)

**Logiikka** (`app/routers/expenses.py`):
1. Hae kaikki viiteet muodossa `YYYY-NNN`
2. Parseaa sekvenssit
3. Etsi max sekvenssä
4. Tarkista seuraava numero ei ole jo käytössä
5. Jos on, inkrementoi kunnes löytyy vapaa

Estää duplikaatit.

---

## 7. ALV-laskenta

`line.gross_amount` ja `line.vat_rate` → lasketaan netto ja ALV:

```python
def _compute_vat(gross, vat_rate):
    if vat_rate <= 0:
        return Decimal("0.00"), gross
    vat_amount = (gross * vat_rate / (100 + vat_rate)).quantize(Decimal("0.01"))
    net = (gross - vat_amount).quantize(Decimal("0.01"))
    return vat_amount, net
```

---

## 8. Migraatiot

Tietokantaa päivitetään automaattisesti (app/database.py):

1. **`_migrate_to_expense_lines`** – Muunta vanhasta single-line muodosta multi-line
2. **`_migrate_category_uniqueness`** – Muuta UNIQUE(name) → UNIQUE(name, category_type)
3. Lisää `expenses.no_receipt` jos sarake puuttuu

Molemmat idempotentit.

---

## 9. Konfiguraatio

### 9.1 Ympäristömuuttujat

```python
DATABASE_URL = "sqlite:///data/accounting.db"
DB_PATH = "data/accounting.db"
DB_PROFILE = "default"
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".pdf", ".webp"}
```

Tietokannan valinnan prioriteetti:
1. `DATABASE_URL`
2. `DB_PATH`
3. `DB_PROFILE` → `data/accounting.db` tai `data/accounting_<profile>.db`

### 9.2 Vaatimukset (requirements.txt)

```
fastapi==0.115.0
uvicorn==0.30.0
sqlalchemy==2.0.49
jinja2==3.1.4
python-multipart==0.0.9
aiofiles==24.1.0
pyyaml==6.0.2
pillow==11.0.0
pymupdf==1.24.0
```

---

## 10. Testitapaukset

### 10.1 Kulun luonti
1. Mene `/expenses/new`
2. Valitse kustannuspaikka, päivä, tyyppi
3. Lisää 2 riviä (eri kategoria, ALV)
4. Lataa kuitti (PDF)
5. Tallenna

**Odotus:** Kulu näkyy listalla, viite-numero on YYYY-NNN-muodossa

### 10.2 Multi-line laskenta
1. Luo kulu 2 rivällä:
   - Rivi 1: 100 € brutto, 24% ALV
   - Rivi 2: 50 € brutto, 0% ALV
2. Tarkista summat näkyvät oikein

**Odotus:**
- Rivi 1: Netto 80.65 €, ALV 19.35 €
- Rivi 2: Netto 50 €, ALV 0 €
- Yhteensä: 150 € brutto, 130.65 € netto, 19.35 € ALV

### 10.3 Raportti
1. Mene `/reports/yearly?cost_center_id=1&year=2026`
2. Klikkaa kategoriaa + merkillä
3. Rivit pitäisi ilmestyä

**Odotus:** Detail-rivit näkyvät, − merkki vaihtaa +

### 10.4 Puuttuvan kuitin varoitus
1. Luo kulu ilman liitettyä kuittia
2. Älä valitse asetusta **Ei kuittia**
3. Avaa vuosiraportti

**Odotus:** Raportti näyttää varoituksen puuttuvasta kuitista

### 10.5 Ei kuittia -poikkeus
1. Luo tai muokkaa kulu ilman kuittia
2. Valitse asetus **Ei kuittia**
3. Avaa vuosiraportti

**Odotus:** Kulu ei näy puuttuvien kuittien varoituslistassa

### 10.6 Tositteiden PDF-yhdistely
1. Avaa vuosiraportti
2. Valitse **Lataa tositteet PDF**
3. Avaa ladattu tiedosto

**Odotus:** Kaikki valitun rajauksen tositteet ovat yhdessä PDF:ssä ja jokaisella sivulla näkyy kuitin tunnus

### 10.7 Kilometrikulu ja ajopäiväkirja
1. Luo uusi kilometrikulu käyttäen kahta riviä (meno ja paluu)
2. Syötä reitti, auto, kilometrit ja €/km
3. Avaa raporttisivulta ajopäiväkirja

**Odotus:** Tapahtumasta muodostuu kilometrikulu ja ajopäiväkirjassa näkyvät molemmat rivit sekä summat

---

## 11. Integraatiot

Ei ulkoisia integraatioita. Kaikki data SQLitessä.

---

## 12. Turvallisuus

- Ei autentikointia (LAN-käyttö)
- CSRF-suoja: Ei toteutettu (HTTPS ei käytössä)
- SQL injection: Suojattu SQLAlchemy ORM:lla
- Tiedoston latailu: Validoitu ekstensio + UUID-nimeäminen

---

## 13. Suorituskyky

- SQLite riittää pienille käyttäjille (<1M rivit)
- PDF-optimointi: 11.5MB → 0.47MB (97% pakkaus)
- Latauksien ylärajoitus: ~50MB muodolliset kuitit

---

## 14. Saatavuus

**Platform:** Windows 10+, Linux, macOS  
**Python:** 3.10+  
**Selain:** Moderni (Chrome, Firefox, Safari, Edge)

---

## 15. Tulevaisuuden laajennukset

- Käyttäjätilien hallinta
- Multi-käyttäjä
- Pilvivarmuus (Google Drive, OneDrive)
- Mobiili-sovellus (React Native)
- Lokalisointi (EN, SV)
- Integratio kirjanpitoohjelmiin (Visma, Tilitoimisto)

---

## 16. Kehitysympäristön setup

### 16.1 Asennus

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows

pip install -r requirements.txt
```

### 16.2 Käynnistys

```bash
.venv\Scripts\uvicorn app.main:app --reload
```

Profiloitu käynnistys eri tietokannoille:

```bash
./start.sh --profile ilkka
start.bat --profile ilkka
```

Avaa `http://127.0.0.1:8000`

### 16.3 Testaaminen

Katso kohta 10 (Testitapaukset).

---

**Tekijä:** Antti  
**Päivitetty:** 2026-04-26
