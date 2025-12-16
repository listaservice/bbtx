# 🎯 BETIX - Platformă SaaS pentru Pariuri Automate

**Platformă multi-tenant pentru pariuri automate pe Betfair Exchange cu strategie de progresie**

[![Status](https://img.shields.io/badge/status-production-success)]()
[![Python](https://img.shields.io/badge/python-3.12-blue)]()
[![Vue.js](https://img.shields.io/badge/vue.js-3-green)]()
[![PostgreSQL](https://img.shields.io/badge/postgresql-16-blue)]()
[![License](https://img.shields.io/badge/license-proprietary-red)]()

---

## 🚀 Quick Start

```bash
# Deploy
./deploy.sh "your commit message"

# Acces Dashboard
http://89.45.83.59
```

---

## 📚 Documentație

**Pentru documentație completă, vezi:**

- **[DOCUMENTATION.md](./DOCUMENTATION.md)** - Documentație completă (arhitectură, funcționalități, API, troubleshooting)
- **[VPS-SETUP.md](./VPS-SETUP.md)** - Setup VPS și deployment

---

## ✨ Features

### Core

- ✅ **Multi-tenant SaaS** - Fiecare user are cont propriu
- ✅ **Plasare automată** pariuri la ore programate
- ✅ **Strategie de progresie** pentru recuperare pierderi
- ✅ **Dashboard web** pentru monitorizare și control
- ✅ **WebSocket** pentru actualizări live

### Subscription & Trial

- ✅ **Trial 10 zile** gratuit la înregistrare
- ✅ **4 planuri**: Simplu (49€), Comun (75€), Extrem (150€), Premium (250€)
- ✅ **Limite echipe** per plan (5/10/25/nelimitat)

### Integrări

- ✅ **Betfair API** - Credențiale per user (criptate AES-256)
- ✅ **Google Sheets** - Spreadsheet dedicat per user
- ✅ **PostgreSQL** - Metadata utilizatori și echipe

### Bot

- ✅ **Miză inițială** configurabilă (default: 10 RON)
- ✅ **Verificare automată** rezultate la 30 min
- ✅ **Filtrare** echipe rezerve/tineret/feminine
- ✅ **Stop loss** la 7 pași progresie

---

## 🏗️ Stack Tehnologic

**Backend:** Python 3.12, FastAPI, SQLAlchemy, PostgreSQL, APScheduler, Betfair API, Google Sheets API
**Frontend:** Vue.js 3, TypeScript, Vite, TailwindCSS, Pinia, Lucide Icons
**Auth:** JWT, bcrypt, AES-256 encryption
**Deployment:** Docker, Railway, VPS Ubuntu 24.04, Nginx

---

## 📊 Strategie

**Formula:** `(pierdere_cumulată / (cotă - 1)) + miză_inițială`

**Exemplu (miză inițială: 10 RON, cotă: 1.5):**

| Step | Pierdere | Miză | Rezultat |
| ---- | -------- | ---- | -------- |
| 0    | 0        | 10   | LOST     |
| 1    | 10       | 30   | LOST     |
| 2    | 40       | 90   | WIN ✅   |

**Profit:** 90 × 1.5 - 130 = **5 RON**

**Caracteristici:**

- Reset automat la WIN
- Stop loss la 7 pași
- Miză inițială configurabilă per echipă (default: 10 RON)

---

## 🔧 Management

```bash
# Status service
sudo systemctl status betfair-bot

# Restart
sudo systemctl restart betfair-bot

# Logs
journalctl -u betfair-bot -f
```

---

## 📞 Info

**VPS:** `89.45.83.59`
**Dashboard:** `http://89.45.83.59`
**API:** `http://89.45.83.59/api`

---

## 📝 Changelog Recent

### v2.1 - 11 Decembrie 2025

- ✅ Trial extins la **10 zile** (de la 3)
- ✅ Miză inițială default **10 RON** (de la 100)
- ✅ Documentație actualizată

### v2.0 - 30 Noiembrie 2025

- ✅ Arhitectură multi-tenant SaaS
- ✅ Autentificare JWT per user
- ✅ Google Sheets dedicat per user
- ✅ Credențiale Betfair criptate AES-256
- ✅ Planuri de abonament

---

**🏆 BETIX - Platformă SaaS de Producție!**
