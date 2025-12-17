# BETIX - Documentație Funcționalități

## 🎯 Descriere Generală

BETIX este un bot automat de pariuri sportive pe Betfair Exchange, bazat pe strategia Martingale modificată. Sistemul este multi-tenant, permițând fiecărui utilizator să aibă propriile credențiale Betfair și Google Sheets.

---

## 🔐 Autentificare & Înregistrare

### Înregistrare User Nou

- **Email + Parolă** → Cont creat automat
- **Trial 10 zile** → Activat automat la înregistrare
- **5 echipe incluse** în trial
- **Google Sheets** → Alocat automat din pool (45 spreadsheet-uri disponibile)
- Spreadsheet-ul e redenumit cu email-ul userului

### Login

- Autentificare JWT
- Token stocat în localStorage
- Redirect automat la dashboard după login

---

## ⚙️ Configurare Betfair (Simplificată)

### Flux Automat (Un Singur Pas)

1. User introduce **username + password Betfair**
2. Backend face login automat pe Betfair Romania (`identitysso.betfair.ro`)
3. Se generează automat **Delayed App Key** pentru user
4. Credențialele sunt **criptate AES-256** și salvate în PostgreSQL
5. Redirect la dashboard

### Credențiale Master vs User

- **Master (tone.claudiu23@gmail.com + SSL cert)** → Folosit pentru:

  - Căutare echipe pe Betfair
  - Fetch meciuri la adăugare echipă
  - Operații **read-only**

- **User (credențiale proprii)** → Folosit pentru:
  - **Plasare pariuri** pe contul propriu
  - Verificare rezultate
  - Operații de betting

---

## 👥 Gestionare Echipe

### Adăugare Echipă

1. Căutare echipă pe Betfair (minim 3 caractere)
2. Selectare din autocomplete
3. Se creează automat:
   - Înregistrare în **Index** (Google Sheets)
   - Foaie dedicată echipei
   - Fetch **următoarele 20 meciuri** cu cote
   - Status **PROGRAMAT** pentru fiecare meci

### Structura Foii Echipă

| Coloană    | Descriere                                    |
| ---------- | -------------------------------------------- |
| Data       | Data și ora meciului (YYYY-MM-DDTHH:MM)      |
| Meci       | Numele meciului (ex: "Man City v Brentford") |
| Competiție | Liga/Competiția                              |
| Cotă       | Cota BACK pentru echipă                      |
| Miză       | Miza plasată (completată la plasare)         |
| Status     | PROGRAMAT → PENDING → WON/LOST               |
| Profit     | Profit/Pierdere (completat la finalizare)    |
| Bet ID     | ID-ul pariului pe Betfair                    |

### Statusuri Meci

- **PROGRAMAT** → Meci găsit, așteaptă plasare pariu
- **PENDING** → Pariu plasat, așteaptă rezultat
- **WON** → Pariu câștigat
- **LOST** → Pariu pierdut
- **ERROR** → Eroare la plasare

---

## 📊 Strategia Martingale Modificată

### Formula de Calcul Miză

```
stake = (cumulative_loss / (odds - 1)) + initial_stake
```

### Principiu

- La **LOST**: `cumulative_loss += stake`, `progression_step += 1`
- La **WON**: Reset `cumulative_loss = 0`, `progression_step = 0`
- Recuperezi toate pierderile + profit egal cu miza inițială

### Exemplu Progresie (stake=10, odds=1.5)

| Step | Loss Cumulat | Miză | Rezultat |
| ---- | ------------ | ---- | -------- |
| 0    | 0            | 10   | LOST     |
| 1    | 10           | 30   | LOST     |
| 2    | 40           | 90   | WIN ✅   |

**Profit final**: 90×1.5 - 130 = **5 RON**

### Stop Loss

- La `progression_step >= 7` → Echipa pe **PAUSE**
- Necesită reset manual

---

## ⏰ Scheduler Automat

### Plasare Pariuri

- **Zilnic la 13:00** (configurabil)
- Verifică toate echipele active
- Plasează pariu pe primul meci PROGRAMAT

### Verificare Rezultate

- **La fiecare 30 minute**
- Verifică pariuri PENDING
- Actualizează status și progresie

### Actualizare Meciuri

- **Zilnic** (configurabil)
- Refresh meciuri pentru toate echipele

### Keep-Alive Betfair

- **La fiecare 4 ore**
- Menține sesiunea activă

---

## 💳 Planuri & Subscripții

### Planuri Disponibile

| Plan         | Preț    | Echipe    | Durată  |
| ------------ | ------- | --------- | ------- |
| Demo (Trial) | Gratuit | 5         | 10 zile |
| Simplu       | 49€     | 5         | 30 zile |
| Comun        | 75€     | 10        | 30 zile |
| Extrem       | 150€    | 25        | 30 zile |
| Premium      | 250€    | Nelimitat | 30 zile |

### Banner Subscription

- Afișează zilele rămase
- Numărul de echipe disponibile
- Data expirării
- Buton Upgrade

---

## 📈 Dashboard

### Statistici Afișate

- Total pariuri
- Pariuri câștigate / pierdute / pending
- Profit total
- Sumă totală pariată
- Grafic evoluție profit

### Echipe Active

- Lista echipelor cu status
- Progresie curentă
- Ultimul pariu

---

## 🔧 Setări

### Configurare Bot

- Ora plasare pariuri (default 13:00)
- Miză inițială (default 10 RON)
- Max progression steps (default 7)

### Test Conexiune Betfair

- Verifică credențialele userului
- Afișează status conexiune

---

## 🗄️ Arhitectură Tehnică

### Backend (FastAPI)

- **Python 3.11+**
- **PostgreSQL** (Supabase) - source of truth
- **SQLAlchemy** ORM
- **httpx** pentru API calls async
- **APScheduler** pentru task-uri programate

### Frontend (Vue.js)

- **Vue 3** + Composition API
- **TypeScript**
- **Tailwind CSS**
- **Axios** pentru API calls
- **Lucide** icons

### Infrastructură

- **VPS**: 89.39.246.58 (Ubuntu 24.04)
- **Nginx** reverse proxy
- **systemd** service management
- **SSL**: Let's Encrypt

### Fișiere Cheie Backend

```
backend/
├── app/
│   ├── api/
│   │   ├── auth.py              # Autentificare
│   │   ├── routes.py            # API endpoints
│   │   └── betfair_setup.py     # Configurare Betfair
│   ├── services/
│   │   ├── betfair_client.py    # Client Betfair API
│   │   ├── google_sheets_multi.py # Google Sheets multi-tenant
│   │   ├── user_bot_service.py  # Logica bot per user
│   │   ├── staking.py           # Formula Martingale
│   │   └── auth_service.py      # Serviciu autentificare
│   ├── models/
│   │   ├── user.py              # Model User
│   │   ├── team.py              # Model Team
│   │   └── betfair_credentials.py # Credențiale criptate
│   └── config.py                # Configurări
```

### Fișiere Cheie Frontend

```
frontend/
├── src/
│   ├── views/
│   │   ├── Dashboard.vue        # Pagina principală
│   │   ├── Teams.vue            # Gestionare echipe
│   │   ├── BetfairSetup.vue     # Configurare Betfair
│   │   ├── Settings.vue         # Setări
│   │   └── Pricing.vue          # Planuri
│   ├── components/
│   │   ├── SubscriptionBanner.vue # Banner trial/subscription
│   │   └── ...
│   └── router/
│       └── index.ts             # Rutare
```

---

## 🔒 Securitate

- **Parole** → bcrypt hash
- **Credențiale Betfair** → AES-256 encryption
- **JWT tokens** → Autentificare API
- **SSL certificates** → HTTPS + Betfair API
- **Environment variables** → Secrets în .env

---

## 📝 Variabile de Mediu (VPS)

```bash
# Database
DATABASE_URL=postgresql://...

# JWT
JWT_SECRET=...
JWT_ALGORITHM=HS256

# Encryption
ENCRYPTION_KEY=...

# Betfair Master (pentru căutări)
BETFAIR_MASTER_APP_KEY=06z7iWIfHewvFOvk
BETFAIR_MASTER_USERNAME=tone.claudiu23@gmail.com
BETFAIR_MASTER_PASSWORD=...
BETFAIR_CERT_PATH=/opt/betfair-bot/certs/betfair.crt
BETFAIR_KEY_PATH=/opt/betfair-bot/certs/betfair.key

# Google Sheets
GOOGLE_SERVICE_ACCOUNT_EMAIL=bbet-953@iempathy-ffc85.iam.gserviceaccount.com
GOOGLE_SHEETS_POOL_FOLDER_ID=1z5I-19J719ox1IIbs6ZZGs8JEcoTwukj
```

---

## 🚀 Deploy

### Comandă Deploy

```bash
./deploy.sh "commit message"
```

### Manual

```bash
cd /opt/betfair-bot
git pull
cd frontend && npm run build
systemctl restart betfair-bot
```

### Logs

```bash
journalctl -u betfair-bot -f
```

---

## ✅ Funcționalități Implementate

- [x] Înregistrare cu alocare automată Google Sheets
- [x] Login/Logout JWT
- [x] Configurare Betfair automată (un singur pas)
- [x] Generare automată App Key
- [x] Căutare echipe pe Betfair
- [x] Adăugare echipă cu fetch meciuri
- [x] Status PROGRAMAT pentru meciuri
- [x] Structură Sheets ca în PARIURI
- [x] Banner trial cu zile rămase
- [x] Dashboard cu statistici
- [x] Gestionare echipe (add/delete/pause)
- [x] Setări bot configurabile
- [x] Multi-tenant (fiecare user izolat)
- [x] Credențiale criptate
- [x] Scheduler automat pentru pariuri

---

_Ultima actualizare: 17 Decembrie 2025_
