#!/usr/bin/env python3
"""
Simple script to test Docling PDF to JSON conversion without authentication.
Uses mocked HTTP responses.
"""

import json
import sys
from pathlib import Path

# Add runner to path (scripts are now in scripts/docling/ subdirectory)
repo_root = Path(__file__).parent.parent.parent
runner_path = repo_root / "runner"
sys.path.insert(0, str(runner_path))

from arazzo_runner import ArazzoRunner

# Import MockHTTPExecutor from tests directory
sys.path.insert(0, str(runner_path / "tests"))
from mocks.http_client import MockHTTPExecutor, MockResponse, RequestMatcher

def create_mock_docling_response():
    """Create a mock HTTP client with Docling response"""
    http_client = MockHTTPExecutor()
    
    # Mock Docling API - Convert PDF to JSON
    # Match any URL containing /v1/convert/file or convert/file
    http_client.add_static_response(
        method="post",
        url_pattern=".*/v1/convert/file.*|.*convert/file.*",
        status_code=200,
        json_data={
            "document": {
                "filename": "test_document.pdf",
                "json_content": {
                    "content": [
                        {
                            "type": "paragraph",
                            "text": "This is a mock PDF document converted to JSON structure."
                        },
                        {
                            "type": "heading",
                            "level": 1,
                            "text": "Sample Document"
                        }
                    ]
                },
                "md_content": "# Sample Document\n\nThis is a mock PDF document converted to JSON structure."
            },
            "status": "success",
            "processing_time": 1.5,
            "errors": []
        }
    )
    
    return http_client

def test_docling_convert():
    """Test Docling PDF to JSON conversion"""
    print("🔄 Testing Docling PDF to JSON Conversion (Mocked)\n")
    
    # Create mock HTTP client
    http_client = create_mock_docling_response()
    
    # Load the Docling OpenAPI spec (scripts are now in scripts/ subdirectory)
    repo_root = Path(__file__).parent.parent
    docling_spec_path = repo_root / "openapi" / "docling.json"
    
    try:
        # Load and modify the spec to add servers if missing
        import json as json_module
        with open(docling_spec_path) as f:
            docling_spec = json_module.load(f)
        
        # Add servers field if it doesn't exist
        if "servers" not in docling_spec or not docling_spec["servers"]:
            docling_spec["servers"] = [
                {
                    "url": "https://api.docling.example.com",
                    "description": "Mock Docling API server"
                }
            ]
        
        # Create source descriptions dict
        source_descriptions = {"docling": docling_spec}
        
        # Initialize runner with mock client and modified spec
        runner = ArazzoRunner(
            source_descriptions=source_descriptions,
            http_client=http_client
        )
        
        # Prepare inputs for the convert operation
        # Note: In real usage, you'd need to provide actual PDF file bytes
        # For this mock test, we'll just show the structure
        inputs = {
            "files": ["mock_pdf_content"],  # In real usage: actual PDF bytes
            "from_formats": ["pdf"],
            "to_formats": ["json"],
            "target_type": "inbody",
            "do_ocr": True,
            "do_table_structure": True
        }
        
        print(f"📥 Operation: process_file_v1_convert_file_post")
        print(f"📥 Inputs: {json.dumps(inputs, indent=2)}\n")
        print("🔄 Executing operation...\n")
        
        # Execute the operation
        result = runner.execute_operation(
            operation_id="process_file_v1_convert_file_post",
            inputs=inputs
        )
        
        # Print results
        print("=" * 60)
        print("📊 Operation Result")
        print("=" * 60)
        print(f"\nStatus Code: {result.get('status_code')}")
        print(f"\nResponse Body:")
        print(json.dumps(result.get('body', {}), indent=2))
        
        if result.get('status_code') == 200:
            print("\n✅ Operation completed successfully!")
            if 'body' in result and 'document' in result['body']:
                json_content = result['body']['document'].get('json_content')
                if json_content:
                    print("\n📄 JSON Content:")
                    print(json.dumps(json_content, indent=2))
        else:
            print(f"\n❌ Operation failed with status: {result.get('status_code')}")
        
        return result
        
    except Exception as e:
        print(f"\n❌ Error executing operation: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    test_docling_convert()
