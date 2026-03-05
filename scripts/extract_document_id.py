#!/usr/bin/env python3
"""
Script to extract document ID from eTenders list documents HTML output.

This script:
1. Calls the eTenders listTenderDocuments endpoint
2. Parses the HTML to extract the first document ID
3. Returns the document ID

Usage:
    python scripts/extract_document_id.py --resource-id 7641353
"""

import argparse
import re
import sys
from pathlib import Path

# Add the runner directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "runner"))

from arazzo_runner import ArazzoRunner


def extract_document_id_from_html(html_content: str) -> str | None:
    """
    Extract the first document ID from HTML content.
    
    Looks for patterns like: downloadDocForAnonymous('DOCUMENT_ID')
    where DOCUMENT_ID is a 7-digit number.
    
    Args:
        html_content: HTML content from listTenderDocuments endpoint
        
    Returns:
        The first 7-digit document ID found, or None if not found
    """
    # Pattern to match downloadDocForAnonymous('7_DIGIT_ID')
    pattern = r"downloadDocForAnonymous\('(\d{7})'\)"
    
    matches = re.findall(pattern, html_content)
    
    if matches:
        return matches[0]  # Return the first match
    
    return None


def main():
    parser = argparse.ArgumentParser(
        description="Extract document ID from eTenders list documents HTML"
    )
    parser.add_argument(
        "--resource-id",
        required=True,
        help="7-digit resource ID for the tender (e.g., 7641353)",
    )
    parser.add_argument(
        "--openapi-path",
        default="./openapi/etenders.json",
        help="Path to eTenders OpenAPI spec file (default: ./openapi/etenders.json)",
    )
    parser.add_argument(
        "--output",
        choices=["id", "json"],
        default="id",
        help="Output format: 'id' for just the ID, 'json' for JSON with details",
    )
    
    args = parser.parse_args()
    
    # Validate resource ID format
    if not re.match(r"^\d{7}$", args.resource_id):
        print(f"Error: resource-id must be a 7-digit number, got: {args.resource_id}", file=sys.stderr)
        sys.exit(1)
    
    try:
        # Initialize the Arazzo Runner with the eTenders OpenAPI spec
        runner = ArazzoRunner.from_openapi_path(args.openapi_path)
        
        # Call the listTenderDocuments operation
        print(f"Calling listTenderDocuments for resourceId: {args.resource_id}...")
        result = runner.execute_operation(
            operation_id="listTenderDocuments",
            inputs={"resourceId": args.resource_id}
        )
        
        if result.get("status_code") != 200:
            print(f"Error: API call failed with status code {result.get('status_code')}", file=sys.stderr)
            print(f"Response: {result.get('body', 'No body')}", file=sys.stderr)
            sys.exit(1)
        
        # Get the HTML content
        html_content = result.get("body", "")
        
        if not html_content:
            print("Error: No HTML content returned from API", file=sys.stderr)
            sys.exit(1)
        
        # Extract the document ID
        document_id = extract_document_id_from_html(html_content)
        
        if not document_id:
            print("Error: Could not find document ID in HTML content", file=sys.stderr)
            print("HTML preview (first 500 chars):", file=sys.stderr)
            print(html_content[:500], file=sys.stderr)
            sys.exit(1)
        
        # Output the result
        if args.output == "json":
            import json
            output = {
                "resourceId": args.resource_id,
                "documentId": document_id,
                "htmlLength": len(html_content),
                "statusCode": result.get("status_code")
            }
            print(json.dumps(output, indent=2))
        else:
            print(document_id)
        
        sys.exit(0)
        
    except FileNotFoundError as e:
        print(f"Error: OpenAPI spec file not found: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
