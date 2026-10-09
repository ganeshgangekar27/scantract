#!/usr/bin/env python3
"""Management routes live check - verify delete, stats, retry without LLM or uploads."""
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
            "full_name": "Mgmt Test"
        })
        assert resp.status_code == 201, f"Register failed: {resp.status_code}"
    
    # Login user A
    resp = client.post(f"{BASE_URL}/api/auth/login", json={"email": email_a, "password": password})
    assert resp.status_code == 200
    data = resp.json()
    token_a = data.get("data", {}).get("access_token") or data.get("access_token")
    client.headers["Authorization"] = f"Bearer {token_a}"
    
    # (a) GET /api/contracts/stats returns 200 with total 0 for new user
    resp = client.get(f"{BASE_URL}/api/contracts/stats")
    check("(a) GET /stats -> 200 with total 0", 
          resp.status_code == 200 and resp.json()["data"]["total"] == 0)
    
    # (b) User A DELETE /api/contracts/46 returns 404/403, then GET /46/report still 200
    resp_delete = client.delete(f"{BASE_URL}/api/contracts/46")
    resp_get = client.get(f"{BASE_URL}/api/contracts/46/report")
    check("(b) DELETE /46 -> 404/403 and GET /46/report -> 200", 
          resp_delete.status_code in [404, 403] and resp_get.status_code == 200)
    
    # (c) DELETE /api/contracts/3 returns 404 (legacy)
    resp = client.delete(f"{BASE_URL}/api/contracts/3")
    check("(c) DELETE /3 -> 404", resp.status_code == 404)
    
    # (d) POST /api/contracts/46/retry returns 409/404 (never 202)
    resp = client.post(f"{BASE_URL}/api/contracts/46/retry")
    check("(d) POST /46/retry -> 409/404 (not 202)", 
          resp.status_code in [409, 404] and resp.status_code != 202)
    
    # (e) User B: DELETE /api/auth/me/data returns 200, then old token gets 401
    resp = client.post(f"{BASE_URL}/api/auth/login", json={"email": email_b, "password": password})
    data = resp.json()
    token_b = data.get("data", {}).get("access_token") or data.get("access_token")
    
    resp_delete = client.delete(
        f"{BASE_URL}/api/auth/me/data",
        headers={"Authorization": f"Bearer {token_b}"}
    )
    
    resp_list = client.get(
        f"{BASE_URL}/api/contracts/list",
        headers={"Authorization": f"Bearer {token_b}"}
    )
    
    check("(e) DELETE /me/data -> 200, then old token -> 401", 
          resp_delete.status_code == 200 and resp_list.status_code == 401)
    
    print("All checks completed")


if __name__ == "__main__":
    main()
