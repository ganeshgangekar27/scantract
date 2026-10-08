#!/usr/bin/env python3
"""Sample contract live check - verify sample access without LLM calls."""
import requests
import secrets

BASE_URL = "http://localhost:8000"


def check(name, condition):
    """Print PASS/FAIL for a check."""
    result = "PASS" if condition else "FAIL"
    print(f"{result}: {name}")
    return condition


def main():
    # Register 2 unique users
    email_a = f"live_{secrets.token_hex(4)}@example.com"
    email_b = f"live_{secrets.token_hex(4)}@example.com"
    password = secrets.token_urlsafe(16)
    
    client = requests.Session()
    client.timeout = 30
    
    # Register users
    for email in [email_a, email_b]:
        resp = client.post(f"{BASE_URL}/api/auth/register", json={
            "email": email,
            "password": password,
            "full_name": "Sample Test"
        })
        assert resp.status_code == 201, f"Register failed: {resp.status_code}"
    
    # (a) No token on GET /api/contracts/list -> 401
    resp = client.get(f"{BASE_URL}/api/contracts/list")
    check("(a) no token list -> 401", resp.status_code == 401)
    
    # Login user A
    resp = client.post(f"{BASE_URL}/api/auth/login", json={"email": email_a, "password": password})
    assert resp.status_code == 200
    data = resp.json()
    token_a = data.get("data", {}).get("access_token") or data.get("access_token")
    client.headers["Authorization"] = f"Bearer {token_a}"
    
    # (b) User A list contains ids 1,44,46,47, each with is_sample true
    resp = client.get(f"{BASE_URL}/api/contracts/list")
    contracts = resp.json()
    sample_ids = [c["contract_id"] for c in contracts if c.get("is_sample")]
    check("(b) list contains 1,44,46,47 as samples", 
          set([1, 44, 46, 47]).issubset(set(sample_ids)))
    
    # (c) A GET /api/contracts/46/report -> 200
    resp = client.get(f"{BASE_URL}/api/contracts/46/report")
    check("(c) GET /46/report -> 200", resp.status_code == 200)
    
    # (d) A GET /api/contracts/46/report/pdf -> 200 and starts with %PDF
    resp = client.get(f"{BASE_URL}/api/contracts/46/report/pdf")
    check("(d) GET /46/report/pdf -> 200 and PDF", 
          resp.status_code == 200 and resp.content[:4] == b'%PDF')
    
    # (e) A GET /api/contracts/57/report -> 404 (belongs to another user)
    resp = client.get(f"{BASE_URL}/api/contracts/57/report")
    check("(e) GET /57/report -> 404", resp.status_code == 404)
    
    # (f) A GET /api/contracts/3/report -> 404 (legacy, not a sample)
    resp = client.get(f"{BASE_URL}/api/contracts/3/report")
    check("(f) GET /3/report -> 404", resp.status_code == 404)
    
    print("All checks completed")


if __name__ == "__main__":
    main()
