# SRIVANI BOOKING MANAGER — Optional Backend Dependencies

## Architecture Decoupling Note
The standard Windows desktop distribution of **SRIVANI BOOKING MANAGER** is 100% self-contained and operates purely on an embedded **SQLite 3** database. It does not require any external database engine, network connectivity, or server dependencies.

---

## Optional Multi-Tenant SaaS Mode

If your organization intends to host the central multi-tenant cloud SaaS backend (introduced in Phase 8) alongside the Windows desktop suite, the following backend components and dependencies are required on the server:

### Server Requirements:
- **Operating System:** Ubuntu 22.04 LTS / Debian 12 / Windows Server 2022
- **Database:** PostgreSQL 14, 15, or 16
- **Python Runtime:** Python 3.10+

### Python Backend Dependencies:
```text
fastapi>=0.110.0
uvicorn[standard]>=0.28.0
pydantic>=2.6.0
pydantic-settings>=2.2.0
sqlalchemy>=2.0.28
alembic>=1.13.1
asyncpg>=0.29.0
psycopg2-binary>=2.9.9
pyjwt>=2.8.0
bcrypt>=4.1.2
```

### Installation & Migration:
```bash
# 1. Install backend dependencies
pip install -r requirements.txt

# 2. Configure environment variables in .env
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=srivani_saas
POSTGRES_USER=srivani_admin
POSTGRES_PASSWORD=your_secure_password
JWT_SECRET=your_jwt_secret_key

# 3. Run Alembic database migrations
alembic upgrade head

# 4. Launch FastAPI server
uvicorn web_app:app --host 0.0.0.0 --port 8000
```

*Note: The standalone desktop installer (`SrivaniBookingManager_Setup_v7.1.0.exe`) deliberately excludes PostgreSQL drivers to ensure minimal footprint and offline desktop reliability.*
