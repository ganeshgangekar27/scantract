"""
End-to-end smoke test for document upload pipeline.
Tests the real FastAPI server with live database.
"""
import time
import tempfile
import os
import requests
import fitz  # PyMuPDF


def create_test_pdf(text: str, output_path: str) -> None:
    """Create minimal PDF with PyMuPDF for testing."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text, fontsize=12)
    doc.save(output_path)
    doc.close()


def main():
    print("=" * 80)
    print("END-TO-END SMOKE TEST: Document Upload Pipeline")
    print("=" * 80)
    
    # Create test PDF with numbered clauses
    test_contract_text = """RENTAL AGREEMENT

1. The Tenant agrees to pay monthly rent of $1,500.00 on the first day of each month.

2. The Landlord shall maintain the property in good and habitable condition at all times.

3. Either party may terminate this agreement with thirty days written notice.

4. The security deposit of $3,000.00 shall be returned within 21 days of move-out."""
    
    # Create temporary PDF file
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
        tmp_path = tmp.name
    
    print(f"\n1. Creating test PDF: {tmp_path}")
    create_test_pdf(test_contract_text, tmp_path)
    print(f"   ✓ Test PDF created with {len(test_contract_text)} characters")
    
    try:
        # Upload to real server
        server_url = "http://localhost:8000/api/contracts/upload"
        print(f"\n2. Uploading to {server_url}")
        
        with open(tmp_path, 'rb') as f:
            files = {'file': ('test_contract.pdf', f, 'application/pdf')}
            response = requests.post(server_url, files=files)
        
        if response.status_code != 200:
            print(f"   ✗ Upload failed with status {response.status_code}")
            print(f"   Response: {response.text}")
            return
        
        result = response.json()
        contract_id = result['contract_id']
        print(f"   ✓ Upload successful!")
        print(f"   - Contract ID: {contract_id}")
        print(f"   - Filename: {result['filename']}")
        print(f"   - Size: {result['size']} bytes")
        print(f"   - Status: {result['status']}")
        
        # Wait for background processing
        print(f"\n3. Waiting 5 seconds for background processing to complete...")
        time.sleep(5)
        
        print(f"\n4. Querying live database...")
        print(f"   Contract ID: {contract_id}")
        
        # Note: Database queries will be run separately via docker exec
        print(f"\n✓ Smoke test script complete. Contract ID: {contract_id}")
        print(f"\nNow run these queries to verify:")
        print(f"")
        print(f"SELECT id, filename, processing_status, page_count, LEFT(full_text, 100)")
        print(f"FROM contracts WHERE id = {contract_id};")
        print(f"")
        print(f"SELECT clause_number, position, LEFT(text, 80)")
        print(f"FROM clauses WHERE contract_id = {contract_id} ORDER BY position;")
        
    finally:
        # Clean up temp file
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
            print(f"\n5. Cleaned up temporary file")


if __name__ == "__main__":
    main()
