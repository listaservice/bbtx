# 📚 BETIX - Documentație Completă

**Platformă SaaS Multi-Tenant pentru Pariuri Automate pe Betfair Exchange**
Versiune: 2.2 | Data: 17 Decembrie 2025

---

## 📋 Cuprins

1. [Prezentare Generală](#prezentare-generală)
2. [Arhitectură](#arhitectură)
3. [Funcționalități](#funcționalități)
4. [Strategia de Pariere](#strategia-de-pariere)
5. [Fluxul Botului](#fluxul-botului)
6. [Dashboard](#dashboard)
7. [Google Sheets](#google-sheets)
8. [API Endpoints](#api-endpoints)
9. [Deployment](#deployment)
10. [Troubleshooting](#troubleshooting)

---

## 🎯 Prezentare Generală

**BETIX** este o platformă SaaS multi-tenant pentru pariuri automate care:

- Oferă **conturi individuale** pentru fiecare utilizator
- Se conectează la **Betfair API** cu credențiale per user (criptate AES-256)
- Gestionează echipe și meciuri în **Google Sheets dedicat per user**
- Stochează metadata în **PostgreSQL**
- Plasează pariuri automat la ore programate
- Folosește o **strategie de progresie** pentru recuperarea pierderilor
- Oferă un **Dashboard web** pentru monitorizare și control

### Planuri de Abonament

| Plan    | Preț      | Echipe    | Trial       |
| ------- | --------- | --------- | ----------- |
| Demo    | Gratuit   | 5         | **10 zile** |
| Simplu  | 49€/lună  | 5         | -           |
| Comun   | 75€/lună  | 10        | -           |
| Extrem  | 150€/lună | 25        | -           |
| Premium | 250€/lună | Nelimitat | -           |

### Stack Tehnologic

**Backend:**

- Python 3.12
- FastAPI
- SQLAlchemy + PostgreSQL
- APScheduler (task scheduling)
- Betfair API Client
- Google Sheets API (gspread)
- JWT + bcrypt (autentificare)
- AES-256 (criptare credențiale)

**Frontend:**

- Vue.js 3 (Composition API)
- TypeScript
- Vite
- TailwindCSS
- Pinia (state management)
- Lucide Vue (icons)

**Deployment:**

- Docker + docker-compose
- Railway (cloud)
- VPS Ubuntu 24.04
- Nginx (reverse proxy)
- systemd (service management)

---

## 🏗️ Arhitectură

```
┌──────────────────────────────────────────────────────────────────────┐
│                      FRONTEND (Vue.js 3)                           │
│  Dashboard │ Teams │ Settings │ History │ Logs │ Pricing │ Login  │
└────────────────────────────────┬─────────────────────────────────────┘
                                │ HTTP/WebSocket (JWT Auth)
┌────────────────────────────────▼─────────────────────────────────────┐
│                        BACKEND (FastAPI)                            │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────────┐       │
│  │ User Bot     │  │ Multi-User    │  │ Auth Service    │       │
│  │ Service      │  │ Scheduler     │  │ (JWT + bcrypt)  │       │
│  └───────────────┘  └───────────────┘  └───────────────────┘       │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────────┐       │
│  │ Betfair      │  │ Google Sheets │  │ Teams           │       │
│  │ Client       │  │ Multi         │  │ Repository      │       │
│  └───────────────┘  └───────────────┘  └───────────────────┘       │
└─────────┬───────────────┬─────────────────┬─────────────────────────┘
          │               │                 │
┌─────────▼─────┐  ┌──────▼────────┐  ┌──────▼──────────┐
│  Betfair API  │  │ Google Sheets │  │   PostgreSQL    │
│  (per user)   │  │ (per user)    │  │   (metadata)    │
└───────────────┘  └───────────────┘  └─────────────────┘
```

---

## ✨ Funcționalități

### 1. Gestionare Echipe

- **Adăugare echipă** cu autocomplete din Betfair
- **Filtrare automată** echipe rezerve/tineret/feminine:
  - `(Res)`, `U19`, `U21`, `U23`
  - `Women`, `Feminin`, `Feminine`
  - `II`, `B)`, `(W)`
- **Actualizare meciuri** zilnică automată
- **Status echipă**: Active / Paused
- **Miză inițială per echipă** (configurabilă individual)

### 2. Plasare Pariuri Automată

- **Programare oră** de pariere (ex: 13:00)
- **Verificare PENDING**: Nu plasează dacă echipa are deja pariu activ
- **Selecție runner corect**: Pariază pe echipa ta, nu pe gazdă
- **Salvare cotă corectă**: Salvează cota echipei tale
- **Actualizare automată** status: PROGRAMAT → PENDING

### 3. Verificare Rezultate

- **Rulare automată** la fiecare 30 minute
- **Verifică pariuri PENDING** pe Betfair
- **Actualizează status**: PENDING → WON/LOST
- **Calculează profit/pierdere**
- **Actualizează progresie** pentru următorul pariu

### 4. Strategie de Progresie

- **Miză inițială** configurabilă per echipă
- **Calcul automat** miză următoare bazat pe pierdere cumulată
- **Stop loss** la 7 pași
- **Reset automat** la WIN
- **Formula**: `(pierdere_cumulată / (cotă - 1)) + miză_inițială`

### 5. Dashboard Web

- **Overview** cu statistici live
- **Teams** cu detalii progresie
- **History** pariuri
- **Settings** configurare bot
- **Logs** în timp real
- **WebSocket** pentru actualizări live

---

## 🎲 Strategia de Pariere

### Principiu

Strategia recuperează pierderile prin creșterea progresivă a mizei, astfel încât la primul WIN să recuperezi toate pierderile anterioare + profit egal cu miza inițială.

### Formula de Calcul

```python
def calculate_stake(cumulative_loss, odds, initial_stake):
    if cumulative_loss <= 0:
        return initial_stake

    stake = (cumulative_loss / (odds - 1)) + initial_stake
    return round(stake, 2)
```

### Exemplu Progresie

**Miză Inițială: 10 RON | Cotă medie: 1.5**

| Step | Pierdere Cumulată | Cotă | Miză Calculată | Rezultat | Profit/Pierdere | Nou Cumulative |
| ---- | ----------------- | ---- | -------------- | -------- | --------------- | -------------- |
| 0    | 0                 | 1.5  | 10             | LOST     | -10             | 10             |
| 1    | 10                | 1.5  | 30             | LOST     | -30             | 40             |
| 2    | 40                | 1.5  | 90             | WIN      | +45             | 0 (RESET)      |

**Total investit:** 10 + 30 + 90 = 130 RON
**Câștig:** 90 × 1.5 = 135 RON
**Profit net:** 135 - 130 = **5 RON** ✅

### Caracteristici Importante

1. **Miză Inițială per Echipă**

   - Fiecare echipă are propria miză inițială
   - Modificabilă oricând din Dashboard
   - Botul folosește automat noua valoare

2. **Reset la WIN**

   - `cumulative_loss = 0`
   - `progression_step = 0`
   - Următorul pariu = miză inițială

3. **Stop Loss**

   - Maxim 7 pași de progresie
   - La pasul 8 → STOP (nu mai pariază)
   - Necesită reset manual

4. **Continuitate Strategie**
   - Dacă modifici miza inițială mid-strategy, botul continuă cu noua valoare
   - Formula rămâne aceeași
   - Profitul se ajustează automat

---

## 🔄 Fluxul Botului

### 1. Adăugare Echipă

```
User → Dashboard → Add Team
  ↓
Search Betfair API (autocomplete)
  ↓
Select Team → Save
  ↓
Create Google Sheet pentru echipă
  ↓
Add to Index sheet cu:
  - cumulative_loss = 0
  - progression_step = 0
  - last_stake = 0
  - initial_stake = 10 RON (din Settings)
  ↓
Fetch meciuri viitoare din Betfair
  ↓
Save în sheet echipă cu status PROGRAMAT
```

### 2. Plasare Pariu (Automată)

```
Scheduler → Ora setată (ex: 13:00)
  ↓
Load echipe ACTIVE din Index
  ↓
Pentru fiecare echipă:
  ├─ Verifică dacă are PENDING bets
  │  └─ Dacă DA → SKIP (nu plasa alt pariu)
  │
  ├─ Citește meciuri PROGRAMAT din sheet
  │  └─ Sortează după dată (cel mai apropiat)
  │
  ├─ Citește date echipă din Index:
  │  ├─ cumulative_loss
  │  ├─ progression_step
  │  └─ initial_stake
  │
  ├─ Calculează miză:
  │  stake = (cumulative_loss / (odds - 1)) + initial_stake
  │
  ├─ Caută meci pe Betfair:
  │  ├─ Match event by name
  │  ├─ Get market (MATCH_ODDS)
  │  └─ Find runner pentru echipa ta (nu gazdă!)
  │
  ├─ Plasează pariu pe Betfair
  │  └─ Primește bet_id
  │
  └─ Update Google Sheets:
     ├─ Sheet echipă: PROGRAMAT → PENDING + stake + bet_id
     └─ Index: last_stake = stake
```

### 3. Verificare Rezultate (La 30 min)

```
Scheduler → Fiecare 30 minute
  ↓
Get toate pariurile PENDING din toate sheets
  ↓
Pentru fiecare pariu PENDING:
  ├─ Verifică status pe Betfair (settled orders)
  │
  ├─ Dacă SETTLED:
  │  ├─ Calculează profit/pierdere
  │  │
  │  ├─ Dacă WON:
  │  │  ├─ profit = stake × (odds - 1)
  │  │  ├─ cumulative_loss = 0
  │  │  └─ progression_step = 0
  │  │
  │  └─ Dacă LOST:
  │     ├─ loss = stake
  │     ├─ cumulative_loss += loss
  │     └─ progression_step += 1
  │
  └─ Update Google Sheets:
     ├─ Sheet echipă: PENDING → WON/LOST + profit
     └─ Index: cumulative_loss, progression_step
```

### 4. Actualizare Meciuri (Zilnică)

```
Scheduler → 12:00 (Europe/Bucharest)
  ↓
Load toate echipele ACTIVE
  ↓
Pentru fiecare echipă:
  ├─ Fetch meciuri viitoare din Betfair
  │  └─ Filtrează reserve/youth/women teams
  │
  ├─ Sortează după dată
  │
  └─ Update sheet echipă:
     ├─ Păstrează meciuri PENDING/WON/LOST
     └─ Adaugă meciuri noi cu status PROGRAMAT
```

---

## 📊 Dashboard

### Pagini

#### 1. Dashboard (Overview)

- **Statistici generale:**
  - Echipe active
  - Profit total
  - Win rate
  - Total pariuri
  - Total mize
- **Status bot:** Running / Stopped
- **Următoarea execuție:** Countdown

#### 2. Teams

- **Lista echipe** cu:
  - Status (Active/Paused)
  - Pierdere cumulată
  - Pas progresie
  - Meciuri (Won/Lost)
  - Profit total
- **Acțiuni:**
  - Pause/Activate
  - Reset progresie
  - Delete echipă
  - **Edit miză inițială** (nou!)
- **Expand** pentru detalii:
  - Sport, Liga, Țară
  - Ultima miză
  - **Miză inițială** (editabilă)
  - Betfair ID
  - Data creării

#### 3. History

- **Lista pariuri** cu filtre:
  - Toate / Pending / Won / Lost
  - Per echipă
- **Detalii pariu:**
  - Meci, Cotă, Miză
  - Status, Profit
  - Bet ID
  - Data

#### 4. Settings

- **Bot Configuration:**
  - Miză inițială (default pentru echipe noi)
  - Ora de pariere
  - Max progression steps
- **Betfair Status:**
  - Conectat / Deconectat
  - Session token valid

#### 5. Logs

- **Logs în timp real** (WebSocket)
- **Filtrare** după nivel (INFO/ERROR/WARNING)
- **Auto-scroll**

---

## 📑 Google Sheets

### Structură

**Spreadsheet:** `Betix - [user_email]`

#### Sheet: Index

Conține metadata pentru toate echipele.

| Coloană          | Tip      | Descriere                          |
| ---------------- | -------- | ---------------------------------- |
| id               | string   | UUID echipă                        |
| name             | string   | Nume echipă                        |
| betfair_id       | string   | ID Betfair (opțional)              |
| sport            | string   | football/basketball                |
| league           | string   | Liga                               |
| country          | string   | Țară                               |
| cumulative_loss  | float    | Pierdere cumulată (RON)            |
| last_stake       | float    | Ultima miză plasată (RON)          |
| progression_step | int      | Pasul curent (0-7)                 |
| status           | string   | active/paused                      |
| created_at       | datetime | Data creării                       |
| updated_at       | datetime | Ultima actualizare                 |
| initial_stake    | float    | **Miză inițială per echipă (RON)** |

#### Sheet: [Nume Echipă]

Fiecare echipă are propriul sheet cu meciuri.

| Coloană    | Tip      | Descriere                  |
| ---------- | -------- | -------------------------- |
| Data       | datetime | Data meciului              |
| Meci       | string   | Nume meci                  |
| Competiție | string   | Liga/Competiție            |
| Cotă       | float    | Cota echipei               |
| Miză       | float    | Miză plasată (RON)         |
| Status     | string   | PROGRAMAT/PENDING/WON/LOST |
| Profit     | float    | Profit/Pierdere (RON)      |
| Bet ID     | string   | ID pariu Betfair           |

**Conditional Formatting:**

- 🟢 WON = verde
- 🔴 LOST = roșu
- 🟡 PENDING = galben
- ⚪ PROGRAMAT = alb

---

## 🔌 API Endpoints

### Teams

```
GET    /api/teams              # Lista echipe
POST   /api/teams              # Adaugă echipă
GET    /api/teams/{id}         # Detalii echipă
PUT    /api/teams/{id}         # Update echipă
DELETE /api/teams/{id}         # Șterge echipă
POST   /api/teams/{id}/pause   # Pause echipă
POST   /api/teams/{id}/activate # Activează echipă
POST   /api/teams/{id}/reset   # Reset progresie
PUT    /api/teams/{id}/initial-stake # Update miză inițială
GET    /api/teams/search-betfair # Search echipe Betfair
POST   /api/teams/{id}/matches # Salvează meciuri
```

### Bot

```
GET  /api/bot/state           # Status bot
POST /api/bot/start           # Pornește bot
POST /api/bot/stop            # Oprește bot
POST /api/bot/run             # Rulează manual
```

### Stats

```
GET /api/stats                # Statistici generale
```

### Settings

```
GET /api/settings             # Citește settings
PUT /api/settings             # Update settings
GET /api/settings/betfair-status # Status Betfair
```

### History

```
GET /api/bets                 # Lista pariuri
```

### Logs

```
GET /api/logs                 # Ultimele log-uri
WS  /ws                       # WebSocket logs live
```

---

## 🚀 Deployment

### VPS Setup

Vezi `VPS-SETUP.md` pentru configurare completă VPS.

### Deploy Script

```bash
./deploy.sh "commit message"
```

**Ce face:**

1. Git add + commit + push
2. SSH pe VPS
3. Pull latest code
4. Restart backend service
5. Rebuild frontend (dacă e nevoie)

### Structură VPS

```
/opt/betfair-bot/
├── backend/
│   ├── app/
│   ├── venv/
│   └── requirements.txt
├── frontend/
│   ├── dist/
│   └── package.json
└── certs/
    ├── client-2048.crt
    └── client-2048.key

/var/www/html/          # Frontend static files
/etc/systemd/system/betfair-bot.service
/etc/nginx/sites-available/betfair-bot
```

### Service Management

```bash
# Status
sudo systemctl status betfair-bot

# Restart
sudo systemctl restart betfair-bot

# Logs
journalctl -u betfair-bot -f

# Stop/Start
sudo systemctl stop betfair-bot
sudo systemctl start betfair-bot
```

---

## 🔧 Troubleshooting

### Bot nu plasează pariuri

**Verificări:**

1. Echipa are status `active`?
2. Există meciuri `PROGRAMAT`?
3. Nu există pariu `PENDING` pentru echipa respectivă?
4. Ora de pariere a trecut?
5. Betfair session valid?

**Logs:**

```bash
journalctl -u betfair-bot -f | grep -i "barcelona\|pariu\|bet"
```

### Eroare "get_pending_bets() takes 1 positional argument"

**Fix:** Funcția a fost actualizată să accepte `team_name` opțional.

### Ultima Miză = 100 RON (greșit)

**Fix:** `last_stake` se actualizează acum automat după plasarea pariului.

### Pariază pe echipa greșită (gazdă în loc de echipa ta)

**Fix:** Botul caută acum runner-ul care conține numele echipei tale, nu primul runner.

### Salvează cota gazdei în loc de cota echipei

**Fix:** Botul salvează acum cota runner-ului selectat (echipa ta).

### Echipe feminine apar în rezultate

**Fix:** Adăugat `(W)` în `skip_keywords`.

### Plasează 2 pariuri pe aceeași echipă

**Fix:** Verificare `PENDING` înainte de plasare.

---

## 📝 Changelog

### v2.1 - 11 Decembrie 2025

**Modificări:**

- ✅ Trial extins la **10 zile** (de la 3 zile)
- ✅ Miză inițială default **10 RON** (de la 100 RON)
- ✅ Documentație actualizată cu structura SaaS
- ✅ README.md actualizat

### v2.0 - 30 Noiembrie 2025

**Features:**

- ✅ **Arhitectură multi-tenant SaaS**
- ✅ **Autentificare JWT** per user
- ✅ **PostgreSQL** pentru metadata utilizatori
- ✅ **Google Sheets dedicat** per user
- ✅ **Credențiale Betfair criptate** AES-256
- ✅ **Planuri de abonament** (Simplu, Comun, Extrem, Premium)
- ✅ **Trial 10 zile** la înregistrare
- ✅ Miză inițială per echipă (configurabilă din Dashboard)
- ✅ UI edit miză în Dashboard cu iconița creion

**Fixes:**

- ✅ Pariază pe echipa corectă (nu gazdă)
- ✅ Salvează cota echipei (nu gazdă)
- ✅ Filtrare echipe feminine `(W)`
- ✅ Verificare PENDING înainte de plasare

### v1.0 - 28 Noiembrie 2025

**Initial Release:**

- Bot automat cu strategie de progresie
- Dashboard Vue.js
- Google Sheets integration
- Betfair API integration
- VPS deployment

---

## 📞 Support

Pentru probleme sau întrebări, verifică:

1. Logs: `journalctl -u betfair-bot -f`
2. Google Sheets pentru date
3. Dashboard pentru status

**VPS:** `89.45.83.59`
**Dashboard:** `http://89.45.83.59`
**API:** `http://89.45.83.59/api`

---

**🏆 BETIX - Platformă SaaS de Producție!**
