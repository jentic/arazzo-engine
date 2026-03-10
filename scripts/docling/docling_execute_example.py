#!/usr/bin/env python3
"""
Example: Execute Docling convert operation using Arazzo Runner

Based on docling_usage.md, this demonstrates how to:
1. Convert a PDF from URL to JSON using the Docling API
2. Use the Arazzo runner's execute-operation command

Usage:
    python docling_execute_example.py
    # Or with a custom PDF URL:
    python docling_execute_example.py "https://arxiv.org/pdf/2206.01062"
"""

import json
import sys
from pathlib import Path

# Add runner to path (scripts are now in scripts/docling/ subdirectory)
repo_root = Path(__file__).parent.parent.parent
runner_path = repo_root / "runner"
sys.path.insert(0, str(runner_path))

from arazzo_runner import ArazzoRunner

def main():
    """Execute Docling convert operation"""
    
    # Get PDF URL from command line or use default
    pdf_url = sys.argv[1] if len(sys.argv) > 1 else "https://arxiv.org/pdf/2206.01062"
    
    print("🔄 Docling PDF to JSON Conversion Example")
    print("=" * 60)
    print(f"📄 PDF URL: {pdf_url}\n")
    
    # Load Docling OpenAPI spec (scripts are now in scripts/ subdirectory)
    repo_root = Path(__file__).parent.parent
    docling_spec_path = repo_root / "openapi" / "docling.json"
    
    # Load and add servers if missing (required by Arazzo)
    with open(docling_spec_path) as f:
        spec = json.load(f)
    
    # Add server configuration based on docling_usage.md
    if "servers" not in spec or not spec["servers"]:
        spec["servers"] = [
            {
                "url": "http://127.0.0.1:5001",
                "description": "Local Docling Serve instance"
            }
        ]
    
    # Create source descriptions
    source_descriptions = {"docling": spec}
    
    # Initialize runner
    # Note: For real execution, you'd use the default HTTP client
    # For testing without a running server, you could use MockHTTPExecutor
    runner = ArazzoRunner(source_descriptions=source_descriptions)
    
    # Prepare inputs based on docling_usage.md structure
    inputs = {
        "sources": [
            {
                "kind": "http",
                "url": pdf_url
            }
        ],
        "options": {
            "to_formats": ["json", "md"],  # Request both JSON and Markdown
            "ocr": False,  # Set to True if OCR is needed
            "pdf_backend": "dlparse_v2",  # Options: pypdfium2, dlparse_v1, dlparse_v2, dlparse_v4
            "table_mode": "fast"  # Options: fast, accurate
        },
        "target": {
            "kind": "inbody"  # Return results in response body
        }
    }
    
    print("📥 Operation: process_url_v1_convert_source_post")
    print("📥 Inputs:")
    print(json.dumps(inputs, indent=2))
    print("\n🔄 Executing operation...\n")
    
    try:
        # Execute the operation
        result = runner.execute_operation(
            operation_id="process_url_v1_convert_source_post",
            inputs=inputs
        )
        
        # Display results
        print("=" * 60)
        print("📊 Operation Result")
        print("=" * 60)
        print(f"\nStatus Code: {result.get('status_code')}\n")
        
        if result.get("status_code") == 200:
            body = result.get("body", {})
            
            # Extract JSON content if available
            document = body.get("document", {})
            json_content = document.get("json_content")
            md_content = document.get("md_content")
            
            print("✅ Operation completed successfully!\n")
            
            # Show status and processing time
            if "status" in body:
                print(f"Status: {body['status']}")
            if "processing_time" in body:
                print(f"Processing Time: {body['processing_time']}s")
            if "errors" in body and body["errors"]:
                print(f"Errors: {body['errors']}")
            
            # Display JSON content if available
            if json_content:
                print("\n📄 JSON Content:")
                print(json.dumps(json_content, indent=2))
            
            # Optionally show markdown preview
            if md_content:
                print(f"\n📝 Markdown Content (first 500 chars):")
                print(md_content[:500] + "..." if len(md_content) > 500 else md_content)
            
            return 0
        else:
            print(f"❌ Operation failed with status: {result.get('status_code')}")
            print("\nResponse Body:")
            print(json.dumps(result.get("body", {}), indent=2))
            return 1
            
    except Exception as e:
        print(f"\n❌ Error executing operation: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
