# Tehnicka specifikacija

## 1. Svrha sistema

Signal Interference Injection Tool je desktop aplikacija (Tkinter + Matplotlib) za:

- ucitavanje cistog signala (PSD po frekvencijskim binovima)
- ucitavanje interferencije
- kombiniranje signala i interferencije u dBm domenu preko linearne snage
- vizualizaciju i izvoz rezultata
- analizu interferiranog signala i izvoz statistike

## 2. Arhitektura

### 2.1 Moduli

- `main.py`
- `tab_interference.py`
- `tab_analysis.py`
- `signal_processing.py`

### 2.2 Odgovornosti

- `main.py`
: inicijalizira Tk aplikaciju i notebook s dva taba.

- `tab_interference.py`
: import clean/interference podataka, parametri interferencije, preview, injekcija i izvoz.

- `tab_analysis.py`
: import interferiranog signala, prikaz po redovima, racun statistike, izvoz statistike.

- `signal_processing.py`
: matematika (dBm/mW), interpolacija, parseri, export helperi.

## 3. Tehnologije i ovisnosti

- Python 3.x
- `numpy`
- `scipy`
- `matplotlib`
- `tkinter` (standardna biblioteka)

Instalacija:

```bash
pip install -r requirements.txt
```

## 4. Funkcionalna specifikacija

### 4.1 Tab Add Interference

Podrzane akcije:

- import clean signala (`CSV`/`DAT`)
- import interference datoteke (`CSV`/`DAT`)
- auto-load Team 4 skupa (`Team_4/signal_data_team_4.csv`, `Team_4/interference_data_team_4.csv`)
- navigacija redova clean signala
- paginacija interferencije
- preview kombiniranog signala
- injekcija i izvoz rezultata

Parametri:

- `Spectrum Width (Hz)`
- `Center Frequency (Hz)`
- `Amplitude Offset (dB)`
- `Vector Length`
- `File Offset`

Strategije mapiranja interferencije na redove clean signala:

- `round_robin`
: red `i` koristi interference page `i % n_pages`

- `one_to_all`
: svi redovi koriste trenutno odabranu interference stranicu

### 4.2 Tab Analyse & Export

Podrzane akcije:

- import interferiranog signala (`CSV`/`DAT`)
- prikaz pojedinog reda
- racun per-bin statistike kroz sve redove
- izvoz statistike (`CSV`)

## 5. Matematikacki model

### 5.1 Pretvorbe jedinica

- dBm -> mW:
`mW = 10^(dBm/10)`

- mW -> dBm:
`dBm = 10 * log10(mW)`

Napomena: kod pretvorbe mW -> dBm koristi se clipping na minimalno `1e-30` kako bi se izbjegao `log(0)`.

### 5.2 Injekcija interferencije

Za svaki bin:

1. clean PSD i interference PSD pretvore se iz dBm u mW
2. linearne snage se zbroje
3. rezultat se vrati u dBm

### 5.3 Interpolacija

Interferencija se linearno interpolira na frekvencijsku mrezu clean signala (`scipy.interpolate.interp1d`).

- izvan izvornog frekvencijskog raspona koristi se fill vrijednost `-120 dBm`

## 6. Specifikacija formata podataka

### 6.1 Clean signal ulaz

Podrzana su 2 formata.

#### Format A: simple numeric

```text
start_freq, stop_freq, psd_1, psd_2, ..., psd_N
```

Pravila:

- delimiter auto-detekcija (`\t`, `;`, `,`)
- ignoriraju se prazni redovi i komentari (`#`)
- ignoriraju se nenumericki redovi
- minimalno 3 numericke vrijednosti po retku

#### Format B: Team 4 tab-delimited

Header:

```text
SEG_START_FREQ\tCENTRE_FREQ\tSEG_STOP_FREQ\tCOUNT\tPSD_MEAS
```

Polja:

- `SEG_START_FREQ`: pocetna frekvencija segmenta
- `CENTRE_FREQ`: srednja frekvencija segmenta
- `SEG_STOP_FREQ`: zavrsna frekvencija segmenta
- `COUNT`: broj PSD tocaka
- `PSD_MEAS`: Python list literal (`[v1, v2, ..., vN]`)

Parser detekcija Team 4 formata:

- prvi red mora sadrzavati `PSD_MEAS`

### 6.2 Interference ulaz

`parse_interference_file` cita sve numericke vrijednosti kao 1D niz.

Podrzane jedinice:

- `dbm`
- `mw`
- `auto`

`auto` pravilo:

- ako je `median(abs(values)) > 200` onda tretira podatke kao `mw`, inace kao `dbm`

### 6.3 Izlazni formati

Interferirani signal (default):

```text
start_freq, stop_freq, psd_1, ..., psd_N
```

Interferirani signal (Team 4 export helper):

```text
SEG_START_FREQ\tCENTRE_FREQ\tSEG_STOP_FREQ\tCOUNT\tPSD_MEAS
```

Statistika:

```text
Frequency (Hz), Mean PSD (dBm), Max PSD (dBm), Min PSD (dBm)
```

## 7. Validirani skupovi u repozitoriju

### 7.1 `Team_4/signal_data_team_4.csv`

- Team 4 format s headerom
- `PSD_MEAS` je lista duljine 401 u uzorku
- `COUNT` u uzorku odgovara broju binova

### 7.2 `Team_4/interference_data_team_4.csv`

- jedna numericka vrijednost po retku
- vrijednosti su velike (`~1e12` u uzorku), pa auto-unit ide u `mw` putanju

### 7.3 `Team_4/injected.csv`, `Team_4/inj2.csv`, `Team_4/inj3.csv`, `Team_4/inj4.csv`

- simple numeric format (bez tekstualnog headera)
- prvi stupci predstavljaju frekvencijski raspon segmenta
- ostatak reda su PSD vrijednosti po binovima

## 8. Operativne napomene

- Matplotlib backend je eksplicitno `TkAgg`.
- Osvjezavanje previewa pri promjeni parametara je debounceano (`200 ms`).
- Oznaka osi frekvencije se prilagodava rasponu (`Hz`, `kHz`, `MHz`, `GHz`).
