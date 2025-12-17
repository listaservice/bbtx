# 🎯 BETIX - Platformă SaaS Multi-Tenant pentru Pariuri Automate

**Platformă multi-tenant pentru pariuri automate pe Betfair Exchange cu strategie de progresie Martingale**

[![Status](https://img.shields.io/badge/status-production-success)]()
[![Python](https://img.shields.io/badge/python-3.12-blue)]()
[![Vue.js](https://img.shields.io/badge/vue.js-3-green)]()
[![PostgreSQL](https://img.shields.io/badge/postgresql-16-blue)]()

---

## 🚀 Quick Start

```bash
# Deploy
./deploy.sh "your commit message"

# Acces Dashboard
http://89.45.83.59
```

---

## ✨ Features

### Core
- ✅ **Multi-tenant SaaS** - Fiecare user are cont propriu, izolare completă
- ✅ **Plasare automată** pariuri zilnic la ora configurată (default 13:00)
- ✅ **Strategie Martingale** pentru recuperare pierderi
- ✅ **Dashboard web** pentru monitorizare și control
- ✅ **WebSocket** pentru actualizări live în timp real

### Subscription & Trial
- ✅ **Trial 10 zile** gratuit la înregistrare
- ✅ **4 planuri**: Simplu (49€), Comun (75€), Extrem (150€), Premium (250€)
- ✅ **Limite echipe** per plan: 5 / 10 / 25 / nelimitat

### Integrări
- ✅ **Betfair API** - Credențiale per user (criptate AES-256 Fernet)
- ✅ **Google Sheets** - Spreadsheet dedicat per user (vizualizare date)
- ✅ **PostgreSQL** - Source of truth pentru users, teams, progresie

### Bot
- ✅ **Miză inițială** configurabilă per echipă (default: 10 RON)
- ✅ **Verificare automată** rezultate la fiecare 30 minute
- ✅ **Filtrare** echipe rezerve/tineret/feminine
- ✅ **Stop loss** la 7 pași progresie (echipa se pune pe PAUSE)

---

## 🏗️ Stack Tehnologic

| Layer | Tehnologii |
|-------|------------|
| **Backend** | Python 3.12, FastAPI, SQLAlchemy, PostgreSQL, APScheduler |
| **Frontend** | Vue.js 3, TypeScript, Vite, TailwindCSS, Pinia |
| **Auth** | JWT, bcrypt, AES-256 encryption (Fernet) |
| **APIs** | Betfair Exchange API, Google Sheets API |
| **Deployment** | Docker, VPS Ubuntu 24.04, Nginx, systemd |

---

## 📊 Strategia Martingale

**Formula:** `miză = (pierdere_cumulată / (cotă - 1)) + miză_inițială`

**Exemplu (miză inițială: 10 RON, cotă: 1.5):**

| Step | Pierdere Cumulată | Miză | Rezultat |
|------|-------------------|------|----------|
| 0    | 0                 | 10   | LOST     |
| 1    | 10                | 30   | LOST     |
| 2    | 40                | 90   | WIN ✅   |

**Profit:** 90 × 1.5 - 130 = **5 RON**

**Caracteristici:**
- **Reset automat la WIN** - cumulative_loss=0, progression_step=0
- **Stop loss la 7 pași** - echipa se pune automat pe PAUSE
- **Miză inițială configurabilă** per echipă din Dashboard

---

## 🔄 Fluxul Complet

```
[1. Înregistrare] → User + Trial 10 zile + Google Sheets nou
        ↓
[2. Setup Betfair] → Credențiale criptate AES-256 în DB
        ↓
[3. Adăugare Echipă] → DB (teams) + Sheets (Index + Team sheet + meciuri)
        ↓
[4. Bot Zilnic 13:00] → Citește DB → Plasează pe Betfair → Update Sheets (PENDING)
        ↓
[5. Check Results 30min] → Betfair settled → Update DB + Sheets (WON/LOST)
```

---

## 🔐 Izolare Multi-Tenant

Fiecare user are **totul separat**:

| Resursă | Izolare |
|---------|---------|
| **Betfair Credentials** | Criptate per user în DB |
| **Google Sheets** | Spreadsheet dedicat per user |
| **Echipe** | Filtrate by `user_id` |
| **Progresie** | Salvată în DB per team |
| **Pariuri** | În spreadsheet-ul propriu |

**Source of Truth:**
- **Database** = users, teams, progresie (cumulative_loss, progression_step)
- **Google Sheets** = vizualizare meciuri și istoric pariuri

---

## 🔧 Management VPS

```bash
# Status service
sudo systemctl status betfair-bot

# Restart
sudo systemctl restart betfair-bot

# Logs live
journalctl -u betfair-bot -f

# Logs ultimele 100 linii
journalctl -u betfair-bot -n 100
```

---

## 🖥️ Development Local

### Prerequisites
- Python 3.12+
- Node.js 20+
- Docker Desktop
- PostgreSQL client

### Start Servicii

```bash
# 1. Docker (PostgreSQL + Redis)
docker-compose -f docker-compose.dev.yml up -d

# 2. Backend (terminal 1)
cd backend
source venv/bin/activate
python -m app.main
# API: http://localhost:8000
# Docs: http://localhost:8000/docs

# 3. Frontend (terminal 2)
cd frontend
npm run dev
# App: http://localhost:5173
```

### Stop Servicii

```bash
# Stop Docker
docker-compose -f docker-compose.dev.yml down
```

---

## 📁 Structura Proiect

```
BETIX LOCAL/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app + schedulers
│   │   ├── config.py            # Settings din .env
│   │   ├── database.py          # SQLAlchemy setup
│   │   ├── dependencies.py      # Auth dependencies
│   │   ├── models/              # SQLAlchemy models
│   │   ├── api/                 # API routes
│   │   │   ├── auth.py          # Login, Register
│   │   │   ├── routes.py        # Teams, Bot, Stats
│   │   │   ├── betfair_setup.py # Betfair credentials
│   │   │   └── websocket.py     # WebSocket updates
│   │   └── services/
│   │       ├── auth_service.py
│   │       ├── user_bot_service.py      # Bot per user
│   │       ├── multi_user_scheduler.py  # Scheduler multi-user
│   │       ├── teams_repository.py      # DB operations
│   │       ├── staking.py               # Formula Martingale
│   │       ├── betfair_client.py        # Betfair API
│   │       ├── google_sheets_multi.py   # Sheets per user
│   │       ├── encryption.py            # AES-256 Fernet
│   │       └── trial_service.py         # Subscription check
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── views/
│   │   │   ├── Register.vue
│   │   │   ├── Login.vue
│   │   │   ├── Dashboard.vue
│   │   │   ├── Teams.vue
│   │   │   ├── BetfairSetup.vue
│   │   │   └── Pricing.vue
│   │   ├── stores/              # Pinia stores
│   │   └── router/
│   └── package.json
│
├── docker-compose.dev.yml
├── deploy.sh
└── README.md
```

---

## 📞 Info Production

| Resource | Value |
|----------|-------|
| **VPS** | 89.45.83.59 |
| **Dashboard** | http://89.45.83.59 |
| **API** | http://89.45.83.59/api |
| **Swagger** | http://89.45.83.59/docs |

---

## 📝 Changelog

### v2.2 - 17 Decembrie 2025
- ✅ Fix `get_team_by_name` în teams_repository
- ✅ Corectare UI trial 3→10 zile
- ✅ Analiză completă și verificare consistență cod

### v2.1 - 11 Decembrie 2025
- ✅ Trial extins la **10 zile** (de la 3)
- ✅ Miză inițială default **10 RON** (de la 100)

### v2.0 - 30 Noiembrie 2025
- ✅ Arhitectură multi-tenant SaaS
- ✅ Autentificare JWT per user
- ✅ Google Sheets dedicat per user
- ✅ Credențiale Betfair criptate AES-256
- ✅ Planuri de abonament cu limite echipe
- ✅ Database = source of truth pentru progresie

---

## ✅ Verificări Funcționalitate

### Fluxuri Verificate (17 Dec 2025)
- ✅ **Înregistrare** - Trial 10 zile, plan Demo, 5 echipe
- ✅ **Login** - JWT auth, verificare subscription expirare
- ✅ **Betfair Setup** - Credențiale criptate AES-256
- ✅ **Adăugare Echipă** - DB + Sheets + fetch meciuri
- ✅ **Strategia Martingale** - Formula corectă, stop loss 7 pași
- ✅ **Plasare Pariu** - Scheduler 13:00, match exact pe runner
- ✅ **Verificare Rezultate** - La 30 min, update DB + Sheets
- ✅ **Izolare Multi-Tenant** - 100% separare per user

---

**🏆 BETIX - Platformă SaaS de Producție!**
