#!/usr/bin/env python3
"""Diagnostic script for auth endpoints."""
import json
import secrets
import string
from urllib.request import Request, urlopen
from urllib.error import HTTPError

BASE = "http://localhost:8000"

def gen_password():
    chars = string.ascii_letters + string.digits + string.punctuation
    return ''.join(secrets.choice(chars) for _ in range(16))

def call(method, path, body=None, token=None):
    url = BASE + path
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if body else None
    req = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode())
    except HTTPError as e:
        return e.code, json.loads(e.read().decode()) if e.headers.get('Content-Type', '').startswith('application/json') else {}

password = gen_password()

# Register
status, resp = call("POST", "/api/auth/register", {
    "email": "diag1@example.com",
    "password": password,
    "full_name": "Diag User"
})
print(f"Register response keys: {list(resp.keys())}")

# Login
status, login_resp = call("POST", "/api/auth/login", {
    "email": "diag1@example.com",
    "password": password
})
print(f"Login response keys: {list(login_resp.keys())}")

# Get token from login
token = login_resp.get("access_token", "")
print(f"Token length: {len(token)}, dot count: {token.count('.')}")

# Call /me with login token
status, me_resp = call("GET", "/api/auth/me", token=token)
print(f"/me with login token: status={status}, body={json.dumps(me_resp)}")

# Try register token if it exists
if "access_token" in resp:
    reg_token = resp["access_token"]
    status, me_resp2 = call("GET", "/api/auth/me", token=reg_token)
    print(f"/me with register token: status={status}, body={json.dumps(me_resp2)}")
