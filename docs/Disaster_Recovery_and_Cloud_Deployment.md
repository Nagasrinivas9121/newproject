# SRIVANI BOOKING MANAGER â€” PHASE 8
## CLOUD DEPLOYMENT & DISASTER RECOVERY RUNBOOK

**Target Standard:** High Availability (99.9% SLA), RPO < 1 hour, RTO < 30 minutes  
**Stack:** Docker Compose, PostgreSQL 16, Redis 7, Nginx Gateway, FastAPI Backend  

---

## 1. PRODUCTION PREREQUISITES

1. **Host Environment**: Linux Server (Ubuntu 22.04 LTS / 24.04 LTS or Debian 12), Minimum 4 vCPU, 8 GB RAM, 100 GB NVMe Storage.
2. **Software Packages**:
   - Docker Engine v25+
   - Docker Compose v2.24+
   - OpenSSL
   - Python 3.12+ (for external backup agents)

---

## 2. PRODUCTION DEPLOYMENT PROCEDURE

### Step 1: Clone and Configure Environment
```bash
git clone https://github.com/organization/srivani-booking-manager.git /opt/srivani
cd /opt/srivani

# Copy environment template
cp .env.example .env

# Generate high-entropy JWT Secret
JWT_SECRET=$(openssl rand -hex 32)
sed -i "s/replace-with-a-64-character-cryptographically-secure-random-string/$JWT_SECRET/" .env

# Generate Strong PostgreSQL Password
DB_PASS=$(openssl rand -hex 24)
sed -i "s/ChangeMeSecurePostgresPassword2026!/$DB_PASS/g" .env
```

### Step 2: Configure TLS / SSL Certificates
For Let's Encrypt:
```bash
mkdir -p nginx/ssl
certbot certonly --standalone -d saas.srivanimanager.com
cp /etc/letsencrypt/live/saas.srivanimanager.com/fullchain.pem nginx/ssl/server.crt
cp /etc/letsencrypt/live/saas.srivanimanager.com/privkey.pem nginx/ssl/server.key
chmod 600 nginx/ssl/server.key
```

### Step 3: Run Database Migrations
```bash
docker compose run --rm api alembic upgrade head
```

### Step 4: Launch Multi-Container Stack
```bash
docker compose up -d --build
docker compose ps
```

### Step 5: Verify Health Checks
```bash
curl -k https://localhost/health
# Response: {"status":"HEALTHY","service":"...","database":"CONNECTED"}
```

---

## 3. AUTOMATED BACKUP SCHEDULE & RETENTION

### 3.1 Backup Frequency Policy
- **Hourly**: Automated WAL (Write-Ahead Logging) archiving.
- **Daily at 02:00 UTC**: Full encrypted database dump + SHA-256 verification.
- **Weekly**: Ticket PDF storage volume snapshot (`storage/tenants`).
- **Retention**: Keep 7 daily backups, 4 weekly backups, 12 monthly backups.

### 3.2 Automated Daily Backup Cron Job
Place the following cron rule in `/etc/cron.d/srivani_backup`:
```cron
0 2 * * * root /usr/bin/python3 /opt/srivani/scripts/backup_recovery_postgres.py --action backup --db-path /opt/srivani/data/srivani_saas.db --backup-dir /var/backups/srivani >> /var/log/srivani_backup.log 2>&1
```

---

## 4. DISASTER RECOVERY & RESTORE RUNBOOK

### Scenario: Database Corruption or Infrastructure Failure
1. **Quarantine Active Services**:
   ```bash
   docker compose stop api nginx
   ```
2. **Select Latest Verified Backup**:
   ```bash
   python3 scripts/backup_recovery_postgres.py --action verify --archive /var/backups/srivani/srivani_backup_YYYYMMDD_HHMMSS.db.gz
   ```
3. **Execute Point-in-Time Restore**:
   ```bash
   python3 scripts/backup_recovery_postgres.py --action restore --archive /var/backups/srivani/srivani_backup_YYYYMMDD_HHMMSS.db.gz --db-path ./data/srivani_saas.db
   ```
4. **Validate Schema & Consistency**:
   ```bash
   alembic upgrade head
   ```
5. **Resume Services & Audit Logs**:
   ```bash
   docker compose up -d
   curl -f http://localhost:8000/health
   ```

---

## 5. MONITORING & ALERTING CONFIGURATION

- **Health Endpoint**: `GET /health` (Polled every 30 seconds by load balancer / Prometheus Blackbox Exporter).
- **Audit Alerts**:
  - `LOGIN_RATE_LIMITED` triggers security alert if > 10 in 5 minutes.
  - `SUBSCRIPTION_UPDATED` or `TENANT_SUSPENDED` notifications dispatched to Super Admin slack/webhook.
