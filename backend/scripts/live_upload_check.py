#!/usr/bin/env python3
"""Live upload proof script - uploads a real contract through the Docker app."""
import secrets
import time
import httpx

BASE_URL = "http://localhost:8000"
PDF_PATH = r"D:\scantract\uploads\temp\20261004_074331_8d357037_Demo_Rental_Agreement_Pune.pdf"

def main():
    # Generate random user
    email = f"live_{secrets.token_hex(4)}@example.com"
    password = secrets.token_urlsafe(16)
    
    client = httpx.Client(base_url=BASE_URL, timeout=30.0)
    
    # Register
    resp = client.post("/api/auth/register", json={
        "email": email,
        "password": password,
        "full_name": "Live Upload Test"
    })
    assert resp.status_code == 201, f"Register failed: {resp.status_code}"
    
    # Login
    resp = client.post("/api/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, f"Login failed: {resp.status_code} {resp.text}"
    data = resp.json()
    token = data.get("data", {}).get("access_token") or data.get("access_token")
    
    # Set auth header
    client.headers["Authorization"] = f"Bearer {token}"
    
    # Upload PDF
    with open(PDF_PATH, "rb") as f:
        files = {"file": ("Demo_Rental_Agreement_Pune.pdf", f, "application/pdf")}
        resp = client.post("/api/contracts/upload", files=files)
    
    assert resp.status_code in (200, 201), f"Upload failed: {resp.status_code} {resp.text}"
    data = resp.json()
    contract_id = data.get("contract_id") or data.get("data", {}).get("contract_id")
    print(f"contract_id={contract_id}")
    
    # Poll for completion
    last_stage = None
    start = time.time()
    max_wait = 540  # 9 minutes
    
    while time.time() - start < max_wait:
        resp = client.get("/api/contracts/list")
        data = resp.json()
        contracts = data if isinstance(data, list) else data.get("data", {}).get("contracts", [])
        if not contracts:
            time.sleep(10)
            continue
        contract = next((c for c in contracts if c.get("id") == contract_id), None)
        
        if not contract:
            time.sleep(10)
            continue
        
        stage = contract["pipeline_stage"]
        if stage != last_stage:
            elapsed = int(time.time() - start)
            print(f"t={elapsed} stage={stage}")
            last_stage = stage
        
        if stage == "failed":
            print(f"failed_stage={contract.get('failed_stage', 'unknown')}")
            print(f"error_message={contract.get('error_message', 'none')}")
            return
        
        if stage == "completed":
            break
        
        time.sleep(10)
    
    # Get report
    resp = client.get(f"/api/contracts/{contract_id}/report")
    print(f"report_status={resp.status_code}")
    
    report = resp.json()["data"]
    print(f"all_clauses={len(report['all_clauses'])}")
    print(f"risky_clauses={len(report['risky_clauses'])}")
    print(f"missing_clauses={len(report['missing_clauses'])}")
    
    risk_summary = report.get("risk_summary", {})
    for key, value in sorted(risk_summary.items()):
        print(f"risk_summary.{key}={value}")
    
    # Check findings quality
    findings = report["risky_clauses"] + report["missing_clauses"]
    empty_citation = sum(1 for f in findings if not f.get("citation"))
    empty_explanation = sum(1 for f in findings if not f.get("explanation"))
    brace_in_explanation = sum(1 for f in findings if "{" in f.get("explanation", "") or "}" in f.get("explanation", ""))
    
    print(f"findings_empty_citation={empty_citation}")
    print(f"findings_empty_explanation={empty_explanation}")
    print(f"findings_with_braces={brace_in_explanation}")
    
    # Print first 14 findings
    for i, finding in enumerate(findings[:14]):
        ftype = "risky" if finding in report["risky_clauses"] else "missing"
        severity = finding.get("severity", "unknown")
        citation = finding.get("citation", "")[:30]
        print(f"{ftype} | {severity} | {citation}")
    
    # Get PDF report
    resp = client.get(f"/api/contracts/{contract_id}/report/pdf")
    print(f"pdf_status={resp.status_code}")
    print(f"pdf_content_type={resp.headers.get('content-type', 'unknown')}")
    print(f"pdf_size={len(resp.content)}")
    print(f"pdf_first_5_bytes={resp.content[:5]}")

if __name__ == "__main__":
    main()
