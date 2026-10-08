"""Tests for sample contract sharing (is_sample flag)."""
import pytest
from sqlalchemy import delete
from httpx import AsyncClient

from app.db.models import Contract, Clause, RiskFinding, User
from app.auth.password import hash_password
from datetime import datetime, timezone


async def create_user(db, email, password):
    user = User(
        email=email, full_name="Test", 
        password_hash=hash_password(password),
        created_at=datetime.now(timezone.utc), is_active=True
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def login(client, email, password):
    resp = await client.post("/api/auth/login", json={"email": email, "password": password})
    token = resp.json().get("access_token") or resp.json().get("data", {}).get("access_token")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
async def cleanup(db_session):
    """Cleanup before and after each test."""
    # Delete by contract_id for findings/clauses (risk_findings.id is UUID, not INTEGER)
    await db_session.execute(delete(RiskFinding).where(RiskFinding.contract_id >= 900000))
    await db_session.execute(delete(Clause).where(Clause.contract_id >= 900000))
    await db_session.execute(delete(Contract).where(Contract.id >= 900000))
    # Delete only test users by exact email pattern
    await db_session.execute(delete(User).where(User.email.in_(['a@example.com', 'b@example.com'])))
    await db_session.commit()
    yield
    # Same cleanup after test
    await db_session.execute(delete(RiskFinding).where(RiskFinding.contract_id >= 900000))
    await db_session.execute(delete(Clause).where(Clause.contract_id >= 900000))
    await db_session.execute(delete(Contract).where(Contract.id >= 900000))
    await db_session.execute(delete(User).where(User.email.in_(['a@example.com', 'b@example.com'])))
    await db_session.commit()


@pytest.mark.asyncio
async def test_sample_read_access(client: AsyncClient, db_session):
    """User B can read sample contract report."""
    user_a = await create_user(db_session, "a@example.com", "pass")
    user_b = await create_user(db_session, "b@example.com", "pass")
    
    contract = Contract(
        id=900001, contract_type="rental", filename="sample.pdf",
        uploaded_at=user_a.created_at, user_id=None, is_sample=True,
        pipeline_stage="completed", processing_status="completed"
    )
    db_session.add(contract)
    
    clause = Clause(
        id=900001, contract_id=900001, clause_id="C1", position=1, text="text",
        clause_type="payment"
    )
    db_session.add(clause)
    
    finding = RiskFinding(
        contract_id=900001, clause_id=900001,
        finding_type="risky_clause", severity="high",
        reason="Test risk", triggering_rule_or_corpus="Test rule",
        explanation="exp", formatted_citation="cite"
    )
    db_session.add(finding)
    await db_session.commit()
    
    headers = await login(client, "b@example.com", "pass")
    resp = await client.get("/api/contracts/900001/report", headers=headers)
    
    assert resp.status_code == 200
    assert len(resp.json()["data"]["all_clauses"]) > 0


@pytest.mark.asyncio
async def test_sample_no_mutation(client: AsyncClient, db_session, monkeypatch):
    """Cannot mutate sample contracts."""
    called = []
    monkeypatch.setattr("app.llm.generate_explanations.generate_all_explanations", lambda *a, **k: called.append(1) or 0)
    
    user = await create_user(db_session, "b@example.com", "pass")
    contract = Contract(
        id=900002, contract_type="rental", filename="sample.pdf",
        uploaded_at=user.created_at, user_id=None, is_sample=True,
        pipeline_stage="completed", processing_status="completed"
    )
    db_session.add(contract)
    await db_session.commit()
    
    headers = await login(client, "b@example.com", "pass")
    resp = await client.post("/api/contracts/900002/explanations/regenerate", headers=headers)
    
    assert resp.status_code == 404
    assert len(called) == 0


@pytest.mark.asyncio
async def test_private_contract_blocked(client: AsyncClient, db_session):
    """User B cannot access A's private contract."""
    user_a = await create_user(db_session, "a@example.com", "pass")
    user_b = await create_user(db_session, "b@example.com", "pass")
    
    contract = Contract(
        id=900003, contract_type="rental", filename="private.pdf",
        uploaded_at=user_a.created_at, user_id=user_a.id, is_sample=False,
        pipeline_stage="completed", processing_status="completed"
    )
    db_session.add(contract)
    await db_session.commit()
    
    headers = await login(client, "b@example.com", "pass")
    resp = await client.get("/api/contracts/900003/report", headers=headers)
    
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_legacy_invisible(client: AsyncClient, db_session):
    """Legacy contracts (NULL, not sample) are 404."""
    user = await create_user(db_session, "b@example.com", "pass")
    
    contract = Contract(
        id=900004, contract_type="rental", filename="legacy.pdf",
        uploaded_at=user.created_at, user_id=None, is_sample=False,
        pipeline_stage="completed", processing_status="completed"
    )
    db_session.add(contract)
    await db_session.commit()
    
    headers = await login(client, "b@example.com", "pass")
    resp = await client.get("/api/contracts/900004/report", headers=headers)
    
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_shows_own_and_samples(client: AsyncClient, db_session):
    """List shows user's contracts + samples, not other users' private."""
    user_a = await create_user(db_session, "a@example.com", "pass")
    user_b = await create_user(db_session, "b@example.com", "pass")
    
    c_a = Contract(
        id=900005, contract_type="rental", filename="a.pdf",
        uploaded_at=user_a.created_at, user_id=user_a.id, is_sample=False,
        pipeline_stage="completed"
    )
    db_session.add(c_a)
    
    c_b = Contract(
        id=900006, contract_type="rental", filename="b.pdf",
        uploaded_at=user_b.created_at, user_id=user_b.id, is_sample=False,
        pipeline_stage="completed"
    )
    db_session.add(c_b)
    
    sample = Contract(
        id=900007, contract_type="freelance", filename="sample.pdf",
        uploaded_at=user_a.created_at, user_id=None, is_sample=True,
        pipeline_stage="completed"
    )
    db_session.add(sample)
    await db_session.commit()
    
    headers = await login(client, "b@example.com", "pass")
    resp = await client.get("/api/contracts/list", headers=headers)
    
    contracts = resp.json()
    ids = [c["contract_id"] for c in contracts]
    
    assert 900006 in ids  # Own contract
    assert 900007 in ids  # Sample
    assert 900005 not in ids  # A's private
    
    sample_item = next(c for c in contracts if c["contract_id"] == 900007)
    assert sample_item["is_sample"] is True


@pytest.mark.asyncio
async def test_sample_requires_auth(client: AsyncClient, db_session):
    """Sample requires auth (no token -> 401)."""
    user = await create_user(db_session, "a@example.com", "pass")
    
    contract = Contract(
        id=900008, contract_type="rental", filename="sample.pdf",
        uploaded_at=user.created_at, user_id=None, is_sample=True,
        pipeline_stage="completed", processing_status="completed"
    )
    db_session.add(contract)
    await db_session.commit()
    
    resp = await client.get("/api/contracts/900008/report")
    
    assert resp.status_code == 401
