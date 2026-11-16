"""
SRIVANI BOOKING MANAGER - PHASE 8 TEST SUITE
Multi-Tenant SaaS Architecture, Security Isolation & RBAC Test Suite
"""

import asyncio
import io
import os
import pytest
import pytest_asyncio
import httpx
from sqlalchemy import select

from server.core.config import settings
from server.core.database import AsyncSessionLocal, init_db
from server.core.security import get_totp_token
from server.main import app, seed_super_admin
from server.models.family import Family
from server.models.tenant import Tenant
from server.models.user import User


@pytest_asyncio.fixture(scope="module", autouse=True)
async def setup_test_environment():
    """Ensure database schema is fresh and super admin seeded."""
    async with AsyncSessionLocal() as db:
        async with db.bind.begin() as conn:
            from server.models import Base
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
    await seed_super_admin()
    yield


@pytest_asyncio.fixture
async def client():
    """Provide an async test client for API interactions."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac


@pytest.mark.asyncio
async def test_01_super_admin_login(client: httpx.AsyncClient):
    """Test bootstrap super admin login and JWT token generation."""
    resp = await client.post(
        "/api/v1/auth/login",
        json={
            "email": settings.SUPER_ADMIN_EMAIL,
            "password": settings.SUPER_ADMIN_PASSWORD,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["role"] == "SUPER_ADMIN"
    assert data["email"] == settings.SUPER_ADMIN_EMAIL.lower()


@pytest.mark.asyncio
async def test_02_invalid_credentials_and_rate_limiting(client: httpx.AsyncClient):
    """Test rejection of invalid credentials and sliding-window rate limiting."""
    bad_email = "nonexistent_attacker@test.com"

    # 1. Invalid login returns 401
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": bad_email, "password": "WrongPassword123!"},
    )
    assert resp.status_code == 401

    # 2. Trigger rate limiter
    for _ in range(settings.RATE_LIMIT_LOGIN_ATTEMPTS_PER_MIN):
        await client.post(
            "/api/v1/auth/login",
            json={"email": bad_email, "password": "WrongPassword123!"},
        )

    rate_limited_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": bad_email, "password": "WrongPassword123!"},
    )
    assert rate_limited_resp.status_code == 429
    assert "Too many failed login attempts" in rate_limited_resp.json()["detail"]


@pytest.mark.asyncio
async def test_03_tenant_provisioning_and_super_admin_boundary(client: httpx.AsyncClient):
    """Test Super Admin provisioning two distinct client tenants."""
    # Login as Super Admin
    admin_login = await client.post(
        "/api/v1/auth/login",
        json={
            "email": settings.SUPER_ADMIN_EMAIL,
            "password": settings.SUPER_ADMIN_PASSWORD,
        },
    )
    admin_token = admin_login.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Provision Tenant A: Tirumala Sewa Trust
    tenant_a_payload = {
        "name": "Tirumala Sewa Trust",
        "slug": "tirumala-sewa",
        "contact_email": "contact@tirumalasewa.org",
        "contact_phone": "+91-9876543210",
        "admin_email": "admin@tirumalasewa.org",
        "admin_password": "TenantA@Secure2026",
        "admin_name": "Ravi Teja",
        "plan_name": "TRIAL",
    }
    resp_a = await client.post("/api/v1/super-admin/tenants", json=tenant_a_payload, headers=admin_headers)
    assert resp_a.status_code == 201

    # Provision Tenant B: Balaji Darshan Travels
    tenant_b_payload = {
        "name": "Balaji Darshan Travels",
        "slug": "balaji-travels",
        "contact_email": "bookings@balajitravels.com",
        "contact_phone": "+91-9876543211",
        "admin_email": "admin@balajitravels.com",
        "admin_password": "TenantB@Secure2026",
        "admin_name": "Suresh Kumar",
        "plan_name": "MONTHLY",
    }
    resp_b = await client.post("/api/v1/super-admin/tenants", json=tenant_b_payload, headers=admin_headers)
    assert resp_b.status_code == 201

    # Verify Super Admin Dashboard shows 2 active clients
    dash_resp = await client.get("/api/v1/super-admin/dashboard", headers=admin_headers)
    assert dash_resp.status_code == 200
    dash_data = dash_resp.json()
    assert dash_data["total_clients"] >= 2
    assert dash_data["active_clients"] >= 2

    # SUPER ADMIN DATA BOUNDARY TEST: Super Admin cannot query devotee/family workspace directly
    cross_access = await client.get("/api/v1/families", headers=admin_headers)
    assert cross_access.status_code == 403
    assert "Super Admin cannot directly access client workspace data" in cross_access.json()["detail"]


@pytest.mark.asyncio
async def test_04_strict_multi_tenant_isolation(client: httpx.AsyncClient):
    """
    CRITICAL SECURITY TEST:
    Verify strict data isolation between Tenant A and Tenant B.
    Tenant A cannot read, modify, or delete Tenant B's families or pilgrims.
    """
    # 1. Login as Tenant A
    login_a = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@tirumalasewa.org", "password": "TenantA@Secure2026"},
    )
    assert login_a.status_code == 200
    token_a = login_a.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # 2. Login as Tenant B
    login_b = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@balajitravels.com", "password": "TenantB@Secure2026"},
    )
    assert login_b.status_code == 200
    token_b = login_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # 3. Tenant A creates Family A1
    fam_a1_payload = {
        "family_id_str": "TST-001",
        "head_name": "Kiran Reddy",
        "contact_number": "9876543210",
        "email": "kiran@example.com",
        "city": "Hyderabad",
        "state": "Telangana",
        "preferred_date": "2026-12-15",
        "priority": "Urgent",
        "status": "Pending",
        "donation_amount": 30000.0,
        "payment_status": "Paid",
    }
    res_fam_a = await client.post("/api/v1/families", json=fam_a1_payload, headers=headers_a)
    assert res_fam_a.status_code == 201
    family_a1 = res_fam_a.json()
    family_a1_id = family_a1["id"]

    # Add a pilgrim to Family A1
    pil_a1_payload = {
        "name": "Kiran Reddy",
        "age": 42,
        "gender": "Male",
        "id_type": "Aadhaar",
        "id_number": "9999-8888-1234",
    }
    res_pil_a = await client.post(
        f"/api/v1/families/{family_a1_id}/pilgrims",
        json=pil_a1_payload,
        headers=headers_a,
    )
    assert res_pil_a.status_code == 201
    pil_a1_data = res_pil_a.json()
    assert pil_a1_data["id_number_masked"] == "XXXX-XXXX-1234"  # Masked PII check

    # 4. Tenant B creates Family B1
    fam_b1_payload = {
        "family_id_str": "BDT-001",
        "head_name": "Narayana Murthy",
        "contact_number": "9876543219",
        "email": "narayana@example.com",
        "city": "Bengaluru",
        "state": "Karnataka",
        "preferred_date": "2026-12-20",
        "priority": "Normal",
        "status": "In Progress",
        "donation_amount": 20000.0,
        "payment_status": "Pending",
    }
    res_fam_b = await client.post("/api/v1/families", json=fam_b1_payload, headers=headers_b)
    assert res_fam_b.status_code == 201
    family_b1 = res_fam_b.json()
    family_b1_id = family_b1["id"]

    # 5. Isolation Check: Tenant A list endpoint must only return Tenant A's family
    list_a = await client.get("/api/v1/families", headers=headers_a)
    assert list_a.status_code == 200
    ids_in_a = [f["id"] for f in list_a.json()]
    assert family_a1_id in ids_in_a
    assert family_b1_id not in ids_in_a

    # Isolation Check: Tenant B list endpoint must only return Tenant B's family
    list_b = await client.get("/api/v1/families", headers=headers_b)
    assert list_b.status_code == 200
    ids_in_b = [f["id"] for f in list_b.json()]
    assert family_b1_id in ids_in_b
    assert family_a1_id not in ids_in_b

    # 6. ATTACK SIMULATION: Tenant A attempts to GET Tenant B's family directly
    cross_get = await client.get(f"/api/v1/families/{family_b1_id}", headers=headers_a)
    assert cross_get.status_code == 404

    # ATTACK SIMULATION: Tenant A attempts to UPDATE Tenant B's family
    cross_put = await client.put(
        f"/api/v1/families/{family_b1_id}",
        json={"head_name": "Hacked Name"},
        headers=headers_a,
    )
    assert cross_put.status_code == 404

    # ATTACK SIMULATION: Tenant A attempts to DELETE Tenant B's family
    cross_del = await client.delete(f"/api/v1/families/{family_b1_id}", headers=headers_a)
    assert cross_del.status_code == 404

    # ATTACK SIMULATION: Tenant B attempts to add a pilgrim to Tenant A's family
    cross_pil_add = await client.post(
        f"/api/v1/families/{family_a1_id}/pilgrims",
        json={"name": "Intruder", "age": 30, "gender": "Male", "id_type": "Aadhaar", "id_number": "1111-2222-3333"},
        headers=headers_b,
    )
    assert cross_pil_add.status_code == 404


@pytest.mark.asyncio
async def test_05_private_ticket_storage_and_tampering_defense(client: httpx.AsyncClient):
    """Test private file storage, MIME/magic byte validation, and cross-tenant download prevention."""
    # Tenant A Login
    login_a = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@tirumalasewa.org", "password": "TenantA@Secure2026"},
    )
    headers_a = {"Authorization": f"Bearer {login_a.json()['access_token']}"}

    # Tenant B Login
    login_b = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@balajitravels.com", "password": "TenantB@Secure2026"},
    )
    headers_b = {"Authorization": f"Bearer {login_b.json()['access_token']}"}

    # Fetch Tenant A's family
    fams_a = (await client.get("/api/v1/families", headers=headers_a)).json()
    fam_a_id = fams_a[0]["id"]

    # 1. Invalid PDF Upload (missing %PDF signature)
    bad_pdf_bytes = b"This is plain text pretending to be a ticket."
    files = {"file": ("fake_ticket.pdf", io.BytesIO(bad_pdf_bytes), "application/pdf")}
    bad_upload = await client.post(
        f"/api/v1/tickets/families/{fam_a_id}/upload",
        files=files,
        headers=headers_a,
    )
    assert bad_upload.status_code == 400
    assert "Invalid file format" in bad_upload.json()["detail"]

    # 2. Valid PDF Upload
    valid_pdf_bytes = b"%PDF-1.4\n%Valid Minimal PDF Document for SRIVANI Booking\n%%EOF"
    files = {"file": ("darshan_ticket_tst001.pdf", io.BytesIO(valid_pdf_bytes), "application/pdf")}
    good_upload = await client.post(
        f"/api/v1/tickets/families/{fam_a_id}/upload",
        files=files,
        headers=headers_a,
    )
    assert good_upload.status_code == 201
    ticket_data = good_upload.json()
    ticket_id = ticket_data["id"]
    assert ticket_data["mime_type"] == "application/pdf"
    assert len(ticket_data["sha256_checksum"]) == 64

    # 3. Authorized Download by Owner Tenant A
    dl_resp = await client.get(f"/api/v1/tickets/{ticket_id}/download", headers=headers_a)
    assert dl_resp.status_code == 200
    assert dl_resp.headers["content-type"] == "application/pdf"
    assert dl_resp.content == valid_pdf_bytes

    # 4. CROSS-TENANT ATTACK: Tenant B attempts to download Tenant A's ticket
    cross_dl = await client.get(f"/api/v1/tickets/{ticket_id}/download", headers=headers_b)
    assert cross_dl.status_code == 404


@pytest.mark.asyncio
async def test_06_tenant_suspension_enforcement(client: httpx.AsyncClient):
    """Test platform administrator suspension and immediate API lockout for suspended tenant."""
    # Super Admin Login
    admin_login = await client.post(
        "/api/v1/auth/login",
        json={"email": settings.SUPER_ADMIN_EMAIL, "password": settings.SUPER_ADMIN_PASSWORD},
    )
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}

    # Fetch Tenant B id
    tenants = (await client.get("/api/v1/super-admin/tenants", headers=admin_headers)).json()
    tenant_b = next(t for t in tenants if t["slug"] == "balaji-travels")
    tenant_b_id = tenant_b["tenant_id"]

    # 1. Suspend Tenant B
    suspend_res = await client.patch(
        f"/api/v1/super-admin/tenants/{tenant_b_id}/status",
        json={"status": "SUSPENDED"},
        headers=admin_headers,
    )
    assert suspend_res.status_code == 200
    assert suspend_res.json()["status"] == "SUSPENDED"

    # 2. Tenant B attempts to login -> 403 Forbidden
    login_attempt = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@balajitravels.com", "password": "TenantB@Secure2026"},
    )
    assert login_attempt.status_code == 403
    assert "suspended" in login_attempt.json()["detail"].lower()

    # 3. Reactivate Tenant B
    reactivate_res = await client.patch(
        f"/api/v1/super-admin/tenants/{tenant_b_id}/status",
        json={"status": "ACTIVE"},
        headers=admin_headers,
    )
    assert reactivate_res.status_code == 200
    assert reactivate_res.json()["status"] == "ACTIVE"


@pytest.mark.asyncio
async def test_07_desktop_data_migration_sync(client: httpx.AsyncClient):
    """Test importing records from desktop migration package and duplicate prevention."""
    # Login as Tenant A
    login_a = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@tirumalasewa.org", "password": "TenantA@Secure2026"},
    )
    headers_a = {"Authorization": f"Bearer {login_a.json()['access_token']}"}

    sync_payload = {
        "source_app": "SRIVANI BOOKING MANAGER Desktop",
        "client_version": "7.0.0",
        "families_count": 2,
        "pilgrims_count": 3,
        "families": [
            {
                "desktop_source_id": 101,
                "family_id_str": "DESK-FAM-101",
                "head_name": "Srinivas Rao",
                "contact_number": "9876543201",
                "email": "srinivas@example.com",
                "status": "Booked",
                "donation_amount": 20000.0,
                "payment_status": "Paid",
                "pilgrims": [
                    {"name": "Srinivas Rao", "age": 45, "gender": "Male", "id_type": "Aadhaar", "id_number": "1234-5678-9012"},
                    {"name": "Lakshmi Rao", "age": 40, "gender": "Female", "id_type": "Aadhaar", "id_number": "1234-5678-9013"},
                ],
            },
            {
                "desktop_source_id": 102,
                "family_id_str": "DESK-FAM-102",
                "head_name": "Venkatesh Prasad",
                "contact_number": "9876543202",
                "status": "Pending",
                "donation_amount": 10000.0,
                "pilgrims": [
                    {"name": "Venkatesh Prasad", "age": 35, "gender": "Male", "id_type": "Passport", "id_number": "Z1234567"},
                ],
            },
        ],
    }

    # 1. First sync run: imports all records
    res_sync1 = await client.post("/api/v1/sync/import-desktop", json=sync_payload, headers=headers_a)
    assert res_sync1.status_code == 200
    data1 = res_sync1.json()
    assert data1["success"] is True
    assert data1["imported_families"] == 2
    assert data1["imported_pilgrims"] == 3
    assert data1["skipped_duplicates"] == 0

    # 2. Duplicate sync run: all records safely skipped without duplication
    res_sync2 = await client.post("/api/v1/sync/import-desktop", json=sync_payload, headers=headers_a)
    assert res_sync2.status_code == 200
    data2 = res_sync2.json()
    assert data2["success"] is True
    assert data2["imported_families"] == 0
    assert data2["skipped_duplicates"] == 2


@pytest.mark.asyncio
async def test_08_totp_mfa_flow(client: httpx.AsyncClient):
    """Test TOTP multi-factor authentication setup and verification."""
    # 1. Login
    login_a = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@tirumalasewa.org", "password": "TenantA@Secure2026"},
    )
    token_a = login_a.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # 2. Initiate MFA Setup
    setup_res = await client.post("/api/v1/auth/mfa/setup", headers=headers_a)
    assert setup_res.status_code == 200
    secret = setup_res.json()["secret"]
    assert "otpauth://" in setup_res.json()["otpauth_uri"]

    # 3. Verify and Enable with valid TOTP
    totp_code = get_totp_token(secret)
    verify_res = await client.post(
        "/api/v1/auth/mfa/verify-and-enable",
        json={"code": totp_code},
        headers=headers_a,
    )
    assert verify_res.status_code == 200
    assert "enabled successfully" in verify_res.json()["message"]

    # 4. Login now requires MFA
    mfa_login_prompt = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@tirumalasewa.org", "password": "TenantA@Secure2026"},
    )
    assert mfa_login_prompt.status_code == 200
    assert mfa_login_prompt.json()["mfa_required"] is True

    # 5. Complete Login with TOTP
    fresh_code = get_totp_token(secret)
    mfa_login_complete = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@tirumalasewa.org", "password": "TenantA@Secure2026", "mfa_code": fresh_code},
    )
    assert mfa_login_complete.status_code == 200
    assert mfa_login_complete.json()["mfa_required"] is False
    assert "access_token" in mfa_login_complete.json()


@pytest.mark.asyncio
async def test_09_audit_log_isolation_and_privacy(client: httpx.AsyncClient):
    """Verify that audit logs are strictly tenant-isolated and contain zero secrets."""
    login_a = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@tirumalasewa.org", "password": "TenantA@Secure2026"},
    )
    # If MFA is required, fetch TOTP
    token_a = login_a.json().get("access_token")
    if login_a.json().get("mfa_required"):
        async with AsyncSessionLocal() as db:
            user = (await db.execute(select(User).where(User.email == "admin@tirumalasewa.org"))).scalars().first()
            code = get_totp_token(user.mfa_secret)
        login_a = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@tirumalasewa.org", "password": "TenantA@Secure2026", "mfa_code": code},
        )
        token_a = login_a.json()["access_token"]

    headers_a = {"Authorization": f"Bearer {token_a}"}

    # Fetch audit logs for Tenant A
    audit_res = await client.get("/api/v1/audit", headers=headers_a)
    assert audit_res.status_code == 200
    logs = audit_res.json()
    assert len(logs) > 0

    # Ensure no passwords or raw credentials exist in logs
    for entry in logs:
        text = entry.get("details_sanitized") or ""
        assert "TenantA@Secure2026" not in text
        assert "SrivaniAdmin@" not in text


@pytest.mark.asyncio
async def test_10_client_dashboard_and_reports(client: httpx.AsyncClient):
    """Test client dashboard metrics and tenant-isolated CSV reporting."""
    # Login as Tenant A
    async with AsyncSessionLocal() as db:
        user = (await db.execute(select(User).where(User.email == "admin@tirumalasewa.org"))).scalars().first()
        code = get_totp_token(user.mfa_secret) if user.mfa_enabled else None

    login_payload = {"email": "admin@tirumalasewa.org", "password": "TenantA@Secure2026"}
    if code:
        login_payload["mfa_code"] = code
    login_a = await client.post("/api/v1/auth/login", json=login_payload)
    headers_a = {"Authorization": f"Bearer {login_a.json()['access_token']}"}

    # 1. Test Client Dashboard
    dash_res = await client.get("/api/v1/client/dashboard", headers=headers_a)
    assert dash_res.status_code == 200
    dash_data = dash_res.json()
    assert dash_data["tenant_name"] == "Tirumala Sewa Trust"
    assert dash_data["total_families"] >= 1
    assert dash_data["plan_name"] == "TRIAL"

    # 2. Test CSV Export
    csv_res = await client.get("/api/v1/reports/csv", headers=headers_a)
    assert csv_res.status_code == 200
    assert "text/csv" in csv_res.headers["content-type"]
    assert "Family ID,Primary Contact" in csv_res.text
    assert "TST-001" in csv_res.text
    # Ensure Tenant B's data is NOT in Tenant A's CSV
    assert "BDT-001" not in csv_res.text


@pytest.mark.asyncio
async def test_11_token_refresh_and_logout_revocation(client: httpx.AsyncClient):
    """Test token refresh and immediate token revocation upon logout."""
    # Login
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": settings.SUPER_ADMIN_EMAIL, "password": settings.SUPER_ADMIN_PASSWORD},
    )
    tokens = login_res.json()
    access_token = tokens["access_token"]
    refresh_token = tokens["refresh_token"]

    # 1. Refresh token
    refresh_res = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh_res.status_code == 200
    new_access_token = refresh_res.json()["access_token"]
    assert new_access_token != access_token

    # 2. Logout with access token
    logout_res = await client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {new_access_token}"},
    )
    assert logout_res.status_code == 200

    # 3. Accessing endpoint with revoked token must fail
    revoked_access = await client.get(
        "/api/v1/super-admin/dashboard",
        headers={"Authorization": f"Bearer {new_access_token}"},
    )
    assert revoked_access.status_code == 401
    assert "revoked" in revoked_access.json()["detail"].lower()


@pytest.mark.asyncio
async def test_12_password_reset_flow(client: httpx.AsyncClient):
    """Test self-service password reset request and token verification."""
    # 1. Request reset
    req_res = await client.post(
        "/api/v1/auth/password-reset-request",
        json={"email": "admin@balajitravels.com"},
    )
    assert req_res.status_code == 200
    reset_token = req_res.json().get("reset_token")
    assert reset_token is not None

    # 2. Confirm reset with new password
    confirm_res = await client.post(
        "/api/v1/auth/password-reset-confirm",
        json={"token": reset_token, "new_password": "NewSecurePassword2026!"},
    )
    assert confirm_res.status_code == 200

    # 3. Old password must fail
    old_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@balajitravels.com", "password": "TenantB@Secure2026"},
    )
    assert old_login.status_code == 401

    # 4. New password succeeds
    new_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@balajitravels.com", "password": "NewSecurePassword2026!"},
    )
    assert new_login.status_code == 200
