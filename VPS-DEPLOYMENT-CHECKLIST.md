# 🚀 VPS DEPLOYMENT CHECKLIST - ROMARG

**VPS Info:**

- IP: 89.45.83.59
- OS: Ubuntu 24.04 LTS
- RAM: 8GB
- CPU: 4 vCPU
- Storage: 160GB NVMe SSD
- Provider: Romarg

---

## ✅ PRE-DEPLOYMENT CHECKLIST

### **1. Database Migration**

**Local → VPS:**

```bash
# 1. Export schema din local
cd /Users/teraki/Desktop/BETIX\ LOCAL/backend
source venv/bin/activate
python -c "from app.database import Base, engine; Base.metadata.create_all(engine)"

# 2. Pe VPS - Rulează migrarea
ssh root@89.45.83.59
cd /opt/betfair-bot/backend
source venv/bin/activate
python migrate_trial.py
```

**Verificare:**

```sql
-- Pe VPS
psql -U betfair_user -d betfair_db
\d users
-- Trebuie să vezi coloana trial_ends_at
```

---

### **2. Dependințe Noi**

**Fișiere de copiat pe VPS:**

```bash
# 1. Servicii noi
backend/app/services/trial_service.py
backend/app/services/encryption.py
backend/app/services/auth_service.py (actualizat)
backend/app/services/google_sheets_multi.py

# 2. Models actualizate
backend/app/models/user.py (cu trial_ends_at)
backend/app/models/subscription.py
backend/app/models/betfair_credentials.py

# 3. API endpoints noi
backend/app/api/auth.py (actualizat)
backend/app/dependencies.py (actualizat)

# 4. Schemas actualizate
backend/app/schemas/user.py (cu trial_ends_at)
backend/app/schemas/auth.py (cu trial_ends_at)

# 5. Main actualizat
backend/app/main.py (cu cron job trial check)

# 6. Migration script
backend/migrate_trial.py
```

---

### **3. Environment Variables (.env pe VPS)**

**Verifică/Adaugă în `/opt/betfair-bot/backend/.env`:**

```bash
# Database (PostgreSQL existent pe VPS)
DATABASE_URL=postgresql://betfair_user:password@localhost:5432/betfair_db

# Redis (TREBUIE INSTALAT!)
REDIS_URL=redis://localhost:6379/0

# Encryption Key (GENEREAZĂ NOU PENTRU PRODUCTION!)
ENCRYPTION_KEY=<generat_cu_fernet>

# JWT (SCHIMBĂ ÎN PRODUCTION!)
JWT_SECRET=production-jwt-secret-very-strong-key
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440

# Stripe (când e gata)
STRIPE_SECRET_KEY=sk_live_...
STRIPE_PUBLISHABLE_KEY=pk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Betfair (deja configurate)
BETFAIR_APP_KEY=06z7iWIfHewvFOvk
BETFAIR_USERNAME=tone.claudiu23@gmail.com
BETFAIR_PASSWORD=Paroladeparior03.

# Google Sheets (deja configurate)
GOOGLE_SHEETS_CREDENTIALS_PATH=./credentials/google_service_account.json

# Bot Config (deja configurate)
BOT_TIMEZONE=Europe/Bucharest
BOT_RUN_HOUR=13
BOT_INITIAL_STAKE=10
BOT_MAX_PROGRESSION_STEPS=7

# Server
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=https://betix.io,http://89.45.83.59

# Development
DEBUG=False
ENVIRONMENT=production
```

---

### **4. Redis Installation pe VPS**

**Redis NU e instalat pe VPS! Trebuie instalat:**

```bash
# SSH pe VPS
ssh root@89.45.83.59

# Instalează Redis
apt update
apt install redis-server -y

# Configurează Redis
systemctl enable redis-server
systemctl start redis-server

# Verificare
redis-cli ping
# Output: PONG

# Configurare securitate (opțional)
nano /etc/redis/redis.conf
# Uncomment: requirepass your_strong_password
systemctl restart redis-server
```

**Dacă folosești password pentru Redis:**

```bash
# În .env
REDIS_URL=redis://:your_strong_password@localhost:6379/0
```

---

### **5. Python Dependencies Update**

**Pe VPS:**

```bash
cd /opt/betfair-bot/backend
source venv/bin/activate

# Update requirements.txt (copiază din local)
# SAU instalează manual:
pip install redis==5.0.1
pip install sqlalchemy==2.0.25
pip install psycopg2-binary==2.9.9
pip install alembic==1.13.1
pip install python-jose[cryptography]==3.3.0
pip install cryptography==42.0.0
pip install stripe==8.0.0

# Verificare
pip list | grep -E "redis|sqlalchemy|alembic|jose|cryptography|stripe"
```

---

### **6. Database Schema Update**

**Opțiune 1: Alembic Migration (recomandat)**

```bash
# Pe VPS
cd /opt/betfair-bot/backend

# Inițializează Alembic (dacă nu e deja)
alembic init alembic

# Creează migrare
alembic revision --autogenerate -m "Add trial system"

# Aplică migrare
alembic upgrade head
```

**Opțiune 2: Manual SQL (rapid)**

```bash
# Pe VPS
psql -U betfair_user -d betfair_db

-- Adaugă coloana
ALTER TABLE users ADD COLUMN IF NOT EXISTS trial_ends_at TIMESTAMP WITHOUT TIME ZONE;

-- Actualizează useri existenți
UPDATE users
SET subscription_plan = 'demo',
    subscription_status = 'trial',
    max_teams = 5,
    trial_ends_at = NOW() + INTERVAL '10 days'
WHERE subscription_status = 'inactive';

-- Verificare
SELECT email, subscription_plan, subscription_status, max_teams, trial_ends_at
FROM users;
```

---

### **7. Systemd Service Update**

**Verifică `/etc/systemd/system/betfair-bot.service`:**

```ini
[Unit]
Description=Betfair Bot API
After=network.target postgresql.service redis-server.service
Requires=postgresql.service redis-server.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/betfair-bot/backend
Environment="PATH=/opt/betfair-bot/backend/venv/bin"
ExecStart=/opt/betfair-bot/backend/venv/bin/python -m app.main
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Reload și restart:**

```bash
systemctl daemon-reload
systemctl restart betfair-bot
systemctl status betfair-bot
```

---

### **8. Nginx Configuration**

**Verifică `/etc/nginx/sites-available/betfair-bot`:**

```nginx
server {
    listen 80;
    server_name 89.45.83.59 betix.io;

    # Frontend
    location / {
        root /opt/betfair-bot/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    # Backend API
    location /api {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket
    location /ws {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "Upgrade";
        proxy_set_header Host $host;
    }

    # Swagger docs
    location /docs {
        proxy_pass http://localhost:8000;
    }
}
```

---

### **9. Frontend Build & Deploy**

**Pe local:**

```bash
cd /Users/teraki/Desktop/BETIX\ LOCAL/frontend

# Build production
npm run build

# Rezultat în: dist/
```

**Pe VPS:**

```bash
# Copiază dist/ pe VPS
scp -r dist/* root@89.45.83.59:/opt/betfair-bot/frontend/dist/

# SAU folosește deploy.sh actualizat
```

---

### **10. Deploy Script Update**

**Actualizează `/Users/teraki/Desktop/BETIX LOCAL/deploy.sh`:**

```bash
#!/bin/bash

echo "🚀 Deploying Betix SaaS to VPS..."

# 1. Git push
git add .
git commit -m "$1"
git push origin main

# 2. SSH și deploy
sshpass -p 'pRv?wkb?p1eDr7' ssh -o StrictHostKeyChecking=no root@89.45.83.59 << 'EOF'
cd /opt/betfair-bot

# Pull latest code
git pull origin main

# Backend
cd backend
source venv/bin/activate

# Install new dependencies
pip install -r requirements.txt

# Run migrations (dacă există)
if [ -f "migrate_trial.py" ]; then
    python migrate_trial.py
fi

# Frontend
cd ../frontend
npm install
npm run build

# Restart services
systemctl restart betfair-bot
systemctl restart nginx

# Check status
systemctl status betfair-bot --no-pager

echo "✅ Deployment complete!"
EOF

echo "🎉 Done!"
```

---

## 🧪 TESTING PE VPS

### **1. Backend Health Check**

```bash
curl http://89.45.83.59:8000/
curl http://89.45.83.59:8000/docs
```

### **2. Redis Check**

```bash
ssh root@89.45.83.59
redis-cli ping
# Output: PONG
```

### **3. Database Check**

```bash
ssh root@89.45.83.59
psql -U betfair_user -d betfair_db -c "\d users"
# Verifică că există trial_ends_at
```

### **4. Trial System Check**

```bash
ssh root@89.45.83.59
cd /opt/betfair-bot/backend
source venv/bin/activate
python test_trial.py
```

### **5. Cron Jobs Check**

```bash
ssh root@89.45.83.59
cd /opt/betfair-bot/backend
source venv/bin/activate
python -c "from app.main import scheduler; print('Scheduler OK')"
```

---

## ⚠️ POTENTIAL ISSUES & SOLUTIONS

### **Issue 1: Redis Not Installed**

```bash
# Error: Connection refused to Redis
# Solution:
apt install redis-server -y
systemctl start redis-server
```

### **Issue 2: PostgreSQL Connection**

```bash
# Error: Could not connect to database
# Solution: Verifică DATABASE_URL în .env
# Format: postgresql://user:password@localhost:5432/database
```

### **Issue 3: Import Errors**

```bash
# Error: ModuleNotFoundError: No module named 'redis'
# Solution:
pip install -r requirements.txt --force-reinstall
```

### **Issue 4: Permission Denied**

```bash
# Error: Permission denied for /opt/betfair-bot
# Solution:
chown -R root:root /opt/betfair-bot
chmod -R 755 /opt/betfair-bot
```

### **Issue 5: Systemd Service Won't Start**

```bash
# Check logs
journalctl -u betfair-bot -n 50 --no-pager

# Check Python errors
cd /opt/betfair-bot/backend
source venv/bin/activate
python -m app.main
```

---

## 📊 MONITORING PE VPS

### **1. Service Status**

```bash
# Check all services
systemctl status betfair-bot
systemctl status nginx
systemctl status postgresql
systemctl status redis-server
```

### **2. Logs**

```bash
# Backend logs
journalctl -u betfair-bot -f

# Nginx logs
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log

# PostgreSQL logs
tail -f /var/log/postgresql/postgresql-*.log
```

### **3. Resource Usage**

```bash
# CPU & Memory
htop

# Disk space
df -h

# Database size
psql -U betfair_user -d betfair_db -c "SELECT pg_size_pretty(pg_database_size('betfair_db'));"
```

---

## 🔒 SECURITY CHECKLIST

### **1. Firewall**

```bash
# Allow only necessary ports
ufw allow 22    # SSH
ufw allow 80    # HTTP
ufw allow 443   # HTTPS (când adaugi SSL)
ufw enable
```

### **2. PostgreSQL**

```bash
# Restrict to localhost only
nano /etc/postgresql/*/main/postgresql.conf
# listen_addresses = 'localhost'
systemctl restart postgresql
```

### **3. Redis**

```bash
# Add password
nano /etc/redis/redis.conf
# requirepass STRONG_PASSWORD_HERE
systemctl restart redis-server
```

### **4. Environment Variables**

```bash
# Protejează .env
chmod 600 /opt/betfair-bot/backend/.env
```

---

## 📅 POST-DEPLOYMENT TASKS

### **Imediat După Deploy:**

- [ ] Verifică backend health: `curl http://89.45.83.59:8000/`
- [ ] Verifică frontend: `http://89.45.83.59/`
- [ ] Test login: `http://89.45.83.59/login`
- [ ] Verifică logs: `journalctl -u betfair-bot -n 50`
- [ ] Test trial system: `python test_trial.py`

### **După 24h:**

- [ ] Verifică cron job trial check (rulează la 00:00)
- [ ] Verifică că userii cu trial expirat sunt suspendați
- [ ] Verifică logs pentru erori

### **Săptămânal:**

- [ ] Backup database
- [ ] Verifică disk space
- [ ] Update dependencies (security patches)

---

## 🎯 ROLLBACK PLAN

**Dacă ceva merge prost:**

```bash
# 1. Revert la versiunea anterioară
ssh root@89.45.83.59
cd /opt/betfair-bot
git log --oneline -5
git checkout <previous_commit_hash>

# 2. Restart services
systemctl restart betfair-bot
systemctl restart nginx

# 3. Verifică că merge
curl http://89.45.83.59:8000/
```

---

## 📞 SUPPORT CONTACTS

**Romarg VPS:**

- Dashboard: https://romarg.ro/clientarea.php
- Support: support@romarg.ro
- Phone: +40 XXX XXX XXX

**Emergency:**

- VPS IP: 89.45.83.59
- SSH: root@89.45.83.59
- Password: pRv?wkb?p1eDr7

---

## ✅ FINAL CHECKLIST ÎNAINTE DE DEPLOY

- [ ] Redis instalat pe VPS
- [ ] Dependencies instalate (requirements.txt)
- [ ] Database migration rulată (trial_ends_at column)
- [ ] .env actualizat cu REDIS_URL și ENCRYPTION_KEY
- [ ] Systemd service actualizat (After=redis-server.service)
- [ ] Frontend build-uit (npm run build)
- [ ] deploy.sh actualizat
- [ ] Backup database făcut
- [ ] Rollback plan pregătit

---

**Document creat:** 30 Noiembrie 2025
**Ultima actualizare:** 30 Noiembrie 2025
**Versiune:** 1.0.0
**Status:** 🟢 Ready for Deployment

---

**🚀 GATA PENTRU DEPLOY PE VPS ROMARG! 🚀**
