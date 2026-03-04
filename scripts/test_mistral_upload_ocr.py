#!/usr/bin/env python3
"""
Test script for Mistral AI file upload and OCR operations.

This script tests the Mistral AI file upload and OCR functionality directly,
bypassing the workflow to debug file upload issues.
"""

import json
import os
import sys
from pathlib import Path

# Add the runner directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "runner"))

from arazzo_runner import ArazzoRunner

def create_test_pdf():
    """Create a simple test PDF file."""
    # Create a minimal PDF (PDF header + basic structure)
    pdf_content = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
/Resources <<
/Font <<
/F1 <<
/Type /Font
/Subtype /Type1
/BaseFont /Helvetica
>>
>>
>>
>>
endobj
4 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
100 700 Td
(Test PDF for Mistral OCR) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000306 00000 n 
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
390
%%EOF"""
    
    test_pdf_path = Path(__file__).parent / "test_document.pdf"
    test_pdf_path.write_bytes(pdf_content)
    print(f"Created test PDF: {test_pdf_path}")
    return test_pdf_path

def test_mistral_upload(runner: ArazzoRunner, pdf_path: Path):
    """Test uploading a file to Mistral AI."""
    print("\n=== Testing Mistral AI File Upload ===")
    
    # Read the PDF file
    pdf_content = pdf_path.read_bytes()
    print(f"PDF size: {len(pdf_content)} bytes")
    
    # Prepare the file dict for multipart upload
    file_dict = {
        "content": pdf_content,
        "file_name": pdf_path.name
    }
    
    # Prepare inputs for the upload operation
    inputs = {
        "file": file_dict,
        "purpose": "ocr"
    }
    
    print(f"Uploading file: {pdf_path.name}")
    print(f"File dict structure: {list(file_dict.keys())}")
    print(f"File content type: {type(file_dict['content'])}")
    print(f"File content size: {len(file_dict['content'])} bytes")
    print(f"Filename: {file_dict['file_name']}")
    
    try:
        result = runner.execute_operation(
            operation_id="files_api_routes_upload_file",
            inputs=inputs
        )
        
        print(f"Upload Status Code: {result.get('status_code')}")
        print(f"Upload Response: {json.dumps(result.get('body'), indent=2)}")
        
        if result.get('status_code') == 200:
            file_id = result.get('body', {}).get('id')
            print(f"✓ File uploaded successfully! File ID: {file_id}")
            return file_id
        else:
            print(f"✗ Upload failed with status {result.get('status_code')}")
            return None
            
    except Exception as e:
        print(f"✗ Upload error: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_mistral_ocr(runner: ArazzoRunner, file_id: str):
    """Test OCR operation with Mistral AI."""
    print("\n=== Testing Mistral AI OCR ===")
    
    if not file_id:
        print("✗ Cannot test OCR: No file_id available")
        return None
    
    # Prepare inputs for OCR operation
    # Use the correct model name: mistral-ocr-latest
    models_to_try = [
        "mistral-ocr-latest",  # The correct model name
        "mistral-ocr-2503-completion",  # Fallback from the example in the spec
        None  # Try without model (let API choose default)
    ]
    
    for model_name in models_to_try:
        print(f"\nTrying model: {model_name or '(default)'}")
        
        inputs = {
            "document": {
                "type": "file",
                "file_id": file_id
            },
            "pages": None,
            "include_image_base64": False
        }
        
        # Only add model if specified
        if model_name:
            inputs["model"] = model_name
        
        try:
            result = runner.execute_operation(
                operation_id="ocr_v1_ocr_post",
                inputs=inputs
            )
            
            print(f"OCR Status Code: {result.get('status_code')}")
            
            if result.get('status_code') == 200:
                body = result.get('body', {})
                pages = body.get('pages', [])
                actual_model = body.get('model', 'unknown')
                print(f"✓ OCR successful! Model used: {actual_model}")
                print(f"✓ Processed {len(pages)} pages")
                
                # Extract text from pages
                if pages:
                    print("\nExtracted text:")
                    for i, page in enumerate(pages, 1):
                        markdown = page.get('markdown', '')
                        print(f"\n--- Page {i} ---")
                        print(markdown[:500] + "..." if len(markdown) > 500 else markdown)
                
                return body
            else:
                error_body = result.get('body', {})
                error_msg = error_body.get('message', 'Unknown error')
                print(f"✗ OCR failed: {error_msg}")
                if model_name != models_to_try[-1]:  # Not the last one
                    print("Trying next model...")
                    continue
                else:
                    print(f"Response: {json.dumps(error_body, indent=2)}")
                    return None
                
        except Exception as e:
            print(f"✗ OCR error: {e}")
            if model_name != models_to_try[-1]:  # Not the last one
                print("Trying next model...")
                continue
            else:
                import traceback
                traceback.print_exc()
                return None
    
    return None

def main():
    """Main test function."""
    print("=" * 60)
    print("Mistral AI File Upload and OCR Test")
    print("=" * 60)
    
    # Check for API key
    api_key = os.getenv("MISTRAL_APIKEY_TOKEN")
    if not api_key:
        print("⚠ Warning: MISTRAL_APIKEY_TOKEN environment variable not set")
        print("Set it with: export MISTRAL_APIKEY_TOKEN='your-api-key'")
        # Continue anyway to see what error we get
    
    # Initialize runner with Mistral AI OpenAPI spec
    openapi_path = Path(__file__).parent.parent / "openapi" / "mistralai.json"
    print(f"\nInitializing runner with: {openapi_path}")
    
    try:
        runner = ArazzoRunner.from_openapi_path(str(openapi_path))
        print("✓ Runner initialized successfully")
    except Exception as e:
        print(f"✗ Failed to initialize runner: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # Create test PDF
    pdf_path = create_test_pdf()
    
    # Test file upload
    file_id = test_mistral_upload(runner, pdf_path)
    
    # Test OCR if upload succeeded
    if file_id:
        ocr_result = test_mistral_ocr(runner, file_id)
        if ocr_result:
            print("\n" + "=" * 60)
            print("✓ All tests passed!")
            print("=" * 60)
            return 0
    
    print("\n" + "=" * 60)
    print("✗ Tests failed")
    print("=" * 60)
    return 1

if __name__ == "__main__":
    sys.exit(main())
