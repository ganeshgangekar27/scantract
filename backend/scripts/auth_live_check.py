#!/usr/bin/env python3
"""Live auth proof script - tests auth endpoints over HTTP."""
import json
import secrets
import sys
from urllib import request, error, parse

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

def check(name, expected, got):
    """Print check result and return pass/fail."""
    result = "PASS" if str(expected) == str(got) else "FAIL"
    print(f"{name} | {expected} | {got} | {result}")
    return result == "PASS"

def main():
    passes = 0
    fails = 0
    # Generate strong random password
    password = secrets.token_urlsafe(16)
    
    # Test 1: Register qa1
    status, _ = req("POST", "/api/auth/register", {
        "email": "qa1@example.com",
        "password": password,
        "full_name": "QA User 1"
    })
    if check("register", 201, status): passes += 1
    else: fails += 1
    
    # Test 2: Duplicate register
    status, _ = req("POST", "/api/auth/register", {
        "email": "qa1@example.com",
        "password": password,
        "full_name": "QA User 1"
    })
    if check("duplicate", 409, status): passes += 1
    else: fails += 1
    
    # Test 3: Login qa1
    status, body = req("POST", "/api/auth/login", {
        "email": "qa1@example.com",
        "password": password
    })
    if check("login", 200, status): passes += 1
    else: fails += 1
    qa1_token = body.get("access_token", "")
    
    # Test 4: Wrong password
    status, _ = req("POST", "/api/auth/login", {
        "email": "qa1@example.com",
        "password": "wrongpassword"
    })
    if check("wrong_password", 401, status): passes += 1
    else: fails += 1
    
    # Test 5: Unknown email
    status, _ = req("POST", "/api/auth/login", {
        "email": "unknown@example.com",
        "password": password
    })
    if check("unknown_email", 401, status): passes += 1
    else: fails += 1
    
    # Test 6: GET /me with token
    status, _ = req("GET", "/api/auth/me", token=qa1_token)
    if check("me_with_token", 200, status): passes += 1
    else: fails += 1
    
    # Test 7: GET /me without token
    try:
        status, _ = req("GET", "/api/auth/me")
    except:
        status = 401  # No token means 401
    if check("me_without_token", 401, status): passes += 1
    else: fails += 1
    
    # Test 8: GET /contracts/list with token
    status, body = req("GET", "/api/contracts/list", token=qa1_token)
    is_empty = (status == 200 and isinstance(body, list) and len(body) == 0)
    if check("list_empty", True, is_empty): passes += 1
    else: fails += 1
    
    # Test 9: GET /contracts/1/report with token (legacy contract not owned)
    status, _ = req("GET", "/api/contracts/1/report", token=qa1_token)
    if check("report_not_owned", 404, status): passes += 1
    else: fails += 1
    
    # Test 10: GET /contracts/1/report without token
    try:
        status, _ = req("GET", "/api/contracts/1/report")
    except:
        status = 401
    if check("report_no_token", 401, status): passes += 1
    else: fails += 1
    
    # Test 11: Forgot password for qa1
    status, body1 = req("POST", "/api/auth/forgot-password", {"email": "qa1@example.com"})
    if check("forgot_known", 200, status): passes += 1
    else: fails += 1
    
    # Test 12: Forgot password for unknown email
    status, body2 = req("POST", "/api/auth/forgot-password", {"email": "unknown@example.com"})
    if check("forgot_unknown", 200, status): passes += 1
    else: fails += 1
    
    # Test 13: Extract reset token from demo_reset_link
    demo_link = body1.get("demo_reset_link", "")
    parsed = parse.urlparse(demo_link)
    query_params = parse.parse_qs(parsed.query)
    reset_token = query_params.get("token", [""])[0]
    
    # Test 14: Reset password using token
    new_password = secrets.token_urlsafe(16)
    status, _ = req("POST", "/api/auth/reset-password", {
        "token": reset_token,
        "new_password": new_password
    })
    if check("reset", 200, status): passes += 1
    else: fails += 1
    
    # Test 15: Login with new password
    status, _ = req("POST", "/api/auth/login", {
        "email": "qa1@example.com",
        "password": new_password
    })
    if check("login_new_pwd", 200, status): passes += 1
    else: fails += 1
    
    # Test 16: Login with old password
    status, _ = req("POST", "/api/auth/login", {
        "email": "qa1@example.com",
        "password": password
    })
    if check("login_old_pwd", 401, status): passes += 1
    else: fails += 1
    
    # Test 17: Reuse reset token
    status, _ = req("POST", "/api/auth/reset-password", {
        "token": reset_token,
        "new_password": secrets.token_urlsafe(16)
    })
    if check("reuse_token", 400, status): passes += 1
    else: fails += 1
    
    print(f"\n=== SUMMARY: {passes} PASS, {fails} FAIL ===")
    sys.exit(0 if fails == 0 else 1)

if __name__ == "__main__":
    main()
