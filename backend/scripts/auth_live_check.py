#!/usr/bin/env python3
"""Live auth proof script - tests auth endpoints over HTTP."""
import json
import secrets
import sys
from urllib import request, error

BASE_URL = "http://localhost:8000"

def req(method, path, data=None, token=None):
    """Make HTTP request, return (status, body_dict)."""
    url = f"{BASE_URL}{path}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    body = json.dumps(data).encode() if data else None
    req_obj = request.Request(url, data=body, headers=headers, method=method)
    
    try:
        with request.urlopen(req_obj) as resp:
            return resp.status, json.loads(resp.read())
    except error.HTTPError as e:
        try:
            body = json.loads(e.read())
        except:
            body = {}
        return e.code, body

def main():
    # Generate strong random password
    password = secrets.token_urlsafe(16)
    
    # Test 1: Register qa1
    status, _ = req("POST", "/api/auth/register", {
        "email": "qa1@example.com",
        "password": password,
        "full_name": "QA User 1"
    })
    print(f"register qa1 | 201 | {status}")
    
    # Test 2: Duplicate register
    status, _ = req("POST", "/api/auth/register", {
        "email": "qa1@example.com",
        "password": password,
        "full_name": "QA User 1"
    })
    print(f"duplicate register | 409 | {status}")
    
    # Test 3: Login qa1
    status, body = req("POST", "/api/auth/login", {
        "email": "qa1@example.com",
        "password": password
    })
    print(f"login qa1 | 200 | {status}")
    qa1_token = body.get("data", {}).get("access_token", "")
    
    # Test 4: Wrong password
    status, _ = req("POST", "/api/auth/login", {
        "email": "qa1@example.com",
        "password": "wrongpassword"
    })
    print(f"wrong password | 401 | {status}")
    
    # Test 5: Unknown email
    status, _ = req("POST", "/api/auth/login", {
        "email": "unknown@example.com",
        "password": password
    })
    print(f"unknown email | 401 | {status}")
    
    # Test 6: GET /me with token
    status, _ = req("GET", "/api/auth/me", token=qa1_token)
    print(f"GET /me with token | 200 | {status}")
    
    # Test 7: GET /me without token
    status, _ = req("GET", "/api/auth/me")
    print(f"GET /me without token | 401 | {status}")
    
    # Test 8: GET /contracts/list with token
    status, body = req("GET", "/api/contracts/list", token=qa1_token)
    is_empty = len(body.get("data", {}).get("contracts", [])) == 0
    print(f"GET /contracts/list with token | empty_list | {is_empty}")
    
    # Test 9: GET /contracts/1/report with token (legacy contract not owned)
    status, _ = req("GET", "/api/contracts/1/report", token=qa1_token)
    print(f"GET /contracts/1/report with token | 404 | {status}")
    
    # Test 10: GET /contracts/1/report without token
    status, _ = req("GET", "/api/contracts/1/report")
    print(f"GET /contracts/1/report without token | 401 | {status}")
    
    # Test 11: Register qa2
    status, _ = req("POST", "/api/auth/register", {
        "email": "qa2@example.com",
        "password": password,
        "full_name": "QA User 2"
    })
    print(f"register qa2 | 201 | {status}")
    
    # Test 12: Forgot password for qa1
    status, body1 = req("POST", "/api/auth/forgot-password", {"email": "qa1@example.com"})
    print(f"forgot-password qa1 | 200 | {status}")
    
    # Test 13: Forgot password for unknown email
    status, body2 = req("POST", "/api/auth/forgot-password", {"email": "unknown@example.com"})
    print(f"forgot-password unknown | 200 | {status}")
    
    # Test 14: Check JSON shapes match
    keys_match = set(body1.keys()) == set(body2.keys())
    has_demo_link = "demo_reset_link" in body1
    print(f"forgot-password shapes match | True | {keys_match}")
    print(f"forgot-password has demo_reset_link | True | {has_demo_link}")
    
    # Test 15: Reset password using token
    reset_token = body1.get("data", {}).get("token", "")
    new_password = secrets.token_urlsafe(16)
    status, _ = req("POST", "/api/auth/reset-password", {
        "token": reset_token,
        "new_password": new_password
    })
    print(f"reset-password with token | 200 | {status}")
    
    # Test 16: Login with new password
    status, _ = req("POST", "/api/auth/login", {
        "email": "qa1@example.com",
        "password": new_password
    })
    print(f"login with new password | 200 | {status}")
    
    # Test 17: Login with old password
    status, _ = req("POST", "/api/auth/login", {
        "email": "qa1@example.com",
        "password": password
    })
    print(f"login with old password | 401 | {status}")
    
    # Test 18: Reuse reset token
    status, _ = req("POST", "/api/auth/reset-password", {
        "token": reset_token,
        "new_password": secrets.token_urlsafe(16)
    })
    print(f"reuse reset token | 400 | {status}")

if __name__ == "__main__":
    main()
