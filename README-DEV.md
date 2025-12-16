# 🚀 BETIX LOCAL - Development Environment

**Folder pentru dezvoltare locală - NU atinge folderul PARIURI (production)!**

---

## 📋 Prerequisites

- ✅ Python 3.8+
- ✅ Node.js 20+
- ✅ Docker Desktop
- ✅ PostgreSQL client (psql)

---

## 🔧 Setup Inițial (Prima Dată)

### 1. Start Servicii Docker (PostgreSQL + Redis)

```bash
# Start PostgreSQL + Redis + Adminer
docker-compose -f docker-compose.dev.yml up -d

# Verificare
docker-compose -f docker-compose.dev.yml ps

# Logs
docker-compose -f docker-compose.dev.yml logs -f
```

**Servicii disponibile:**

- PostgreSQL: `localhost:5432`
- Redis: `localhost:6379`
- Adminer (DB UI): `http://localhost:8080`

### 2. Setup Backend

```bash
cd backend

# Creează virtual environment
python3 -m venv venv

# Activează venv
source venv/bin/activate

# Instalează dependințe
pip install -r requirements.txt

# Instalează dependințe SaaS (noi)
pip install sqlalchemy psycopg2-binary alembic redis python-jose[cryptography] passlib[bcrypt] stripe

# Salvează requirements actualizat
pip freeze > requirements.txt

# Copiază .env.local ca .env
cp .env.local .env

# Editează .env cu credențialele tale
nano .env
```

### 3. Setup Database (Migrări)

```bash
# Creează tabele (când vom avea migrări Alembic)
alembic upgrade head

# SAU manual pentru început
python -c "from app.database import create_tables; create_tables()"
```

### 4. Setup Frontend

```bash
cd frontend

# Instalează dependințe
npm install

# Instalează dependințe SaaS (noi)
npm install @stripe/stripe-js

# Verifică .env.local
cat .env.local
```

---

## 🏃 Rulare Zilnică

### Start Servicii

```bash
# 1. Start Docker services (dacă nu rulează)
docker-compose -f docker-compose.dev.yml up -d

# 2. Start Backend (terminal 1)
cd backend
source venv/bin/activate
python -m app.main

# Backend disponibil:
# - API: http://localhost:8000
# - Docs: http://localhost:8000/docs
# - Redoc: http://localhost:8000/redoc

# 3. Start Frontend (terminal 2)
cd frontend
npm run dev

# Frontend disponibil:
# - App: http://localhost:5173
```

### Stop Servicii

```bash
# Stop backend: Ctrl+C în terminal

# Stop frontend: Ctrl+C în terminal

# Stop Docker services
docker-compose -f docker-compose.dev.yml down

# Stop și șterge volume (ATENȚIE: șterge datele!)
docker-compose -f docker-compose.dev.yml down -v
```

---

## 🧪 Testing

### Backend Tests

```bash
cd backend
source venv/bin/activate
pytest

# Cu coverage
pytest --cov=app --cov-report=html
```

### Frontend Tests

```bash
cd frontend
npm run test

# E2E tests
npm run test:e2e
```

---

## 🗄️ Database Management

### Accesare PostgreSQL

```bash
# Via psql
psql -h localhost -U betix -d betix_dev
# Password: betix_dev_pass

# Via Adminer (UI)
# Browser: http://localhost:8080
# System: PostgreSQL
# Server: postgres
# Username: betix
# Password: betix_dev_pass
# Database: betix_dev
```

### Comenzi Utile

```sql
-- Lista tabele
\dt

-- Structura tabel
\d users

-- Query
SELECT * FROM users;

-- Exit
\q
```

---

## 🔄 Git Workflow

### Dezvoltare Feature Nou

```bash
# Creează branch
git checkout -b feature/saas-auth

# Lucrezi pe cod...
# ...

# Commit
git add .
git commit -m "Add: Multi-user authentication"

# Push
git push origin feature/saas-auth

# Merge în main (după review)
git checkout main
git merge feature/saas-auth
```

### Sync cu Production

```bash
# Pull ultimele modificări din production
cd /Users/teraki/Desktop/PARIURI
git pull

# Copiază modificări în BETIX LOCAL
cd /Users/teraki/Desktop/BETIX\ LOCAL
git pull
```

---

## 📦 Deploy pe VPS

### Când ești gata cu feature-ul

```bash
# 1. Asigură-te că totul e testat local
npm run test
pytest

# 2. Commit și push
git add .
git commit -m "Add: Feature X"
git push origin main

# 3. Deploy pe VPS (din folderul PARIURI)
cd /Users/teraki/Desktop/PARIURI
./deploy.sh "Add: Feature X"
```

---

## 🛠️ Troubleshooting

### PostgreSQL nu pornește

```bash
# Verifică dacă portul 5432 e ocupat
lsof -i :5432

# Oprește PostgreSQL local (dacă rulează)
brew services stop postgresql@14

# Restart Docker container
docker-compose -f docker-compose.dev.yml restart postgres
```

### Redis nu pornește

```bash
# Verifică dacă portul 6379 e ocupat
lsof -i :6379

# Restart Docker container
docker-compose -f docker-compose.dev.yml restart redis
```

### Backend erori

```bash
# Verifică logs
docker-compose -f docker-compose.dev.yml logs postgres
docker-compose -f docker-compose.dev.yml logs redis

# Verifică .env
cat backend/.env

# Reinstalează dependințe
cd backend
source venv/bin/activate
pip install -r requirements.txt --force-reinstall
```

### Frontend erori

```bash
# Clear cache
cd frontend
rm -rf node_modules
rm package-lock.json
npm install

# Verifică .env.local
cat .env.local
```

---

## 📊 Structura Proiect

```
BETIX LOCAL/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py          ← NOU (SQLAlchemy)
│   │   ├── models/              ← NOU (User, Subscription, etc.)
│   │   ├── schemas/             ← NOU (Pydantic schemas)
│   │   ├── services/
│   │   │   ├── auth.py          ← NOU (JWT, passwords)
│   │   │   ├── stripe.py        ← NOU (payments)
│   │   │   ├── google_sheets_multi.py  ← NOU (per user)
│   │   │   └── ...
│   │   └── api/
│   │       ├── auth.py          ← NOU (login, register)
│   │       ├── users.py         ← NOU (profile, settings)
│   │       └── ...
│   ├── alembic/                 ← NOU (DB migrations)
│   ├── tests/                   ← NOU (unit tests)
│   ├── .env.local
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── views/
│   │   │   ├── Register.vue     ← NOU
│   │   │   ├── Login.vue        ← NOU
│   │   │   ├── Pricing.vue      ← NOU
│   │   │   ├── Billing.vue      ← NOU
│   │   │   └── ...
│   │   ├── stores/
│   │   │   ├── auth.ts          ← NOU (Pinia store)
│   │   │   └── ...
│   │   └── router/
│   │       └── index.ts         ← Actualizat (auth guards)
│   ├── .env.local
│   └── package.json
│
├── docker-compose.dev.yml       ← NOU
└── README-DEV.md                ← NOU (acest fișier)
```

---

## ✅ Checklist Dezvoltare

### Setup Inițial

- [ ] Docker services running
- [ ] PostgreSQL conectat
- [ ] Redis conectat
- [ ] Backend .env configurat
- [ ] Frontend .env.local configurat
- [ ] Dependințe instalate

### Înainte de Deploy

- [ ] Toate testele trec
- [ ] Cod reviewed
- [ ] .env production actualizat pe VPS
- [ ] Database migrations pregătite
- [ ] Frontend build testat

---

## 🎯 Status Implementare

### ✅ Completat (v2.1)

1. **Faza 1:** ✅ Setup PostgreSQL + Auth + Encryption
2. **Faza 2:** ✅ Multi-tenancy + Google Sheets per user
3. **Faza 3:** ⏸️ Stripe integration (pregătit, neactivat)
4. **Faza 4:** ✅ Frontend SaaS (Register, Login, Pricing, Betfair Setup)
5. **Faza 5:** ✅ Deploy production

### 📋 Configurări Actuale

- **Trial:** 10 zile (la înregistrare)
- **Miză inițială:** 10 RON (default)
- **Planuri:** Demo, Simplu (49€), Comun (75€), Extrem (150€), Premium (250€)

### 🔜 De Făcut (Producție)

- [ ] Activare Stripe pentru plăți reale
- [ ] Rate limiting pe API
- [ ] WebSocket authentication
- [ ] Teste unitare
- [ ] Credențiale production în .env

---

**Happy Coding! 🚀**
