#!/usr/bin/env python3
"""
Test script to verify that descriptions appear in extracted inputs.
Tests the changes to extract_operation_io function using nyt.json.
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any

# Add the runner directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "runner"))

from arazzo_runner.extractor.openapi_extractor import extract_operation_io


def load_nyt_spec() -> Dict[str, Any]:
    """Load the NYT API specification from nyt.json."""
    nyt_path = Path(__file__).parent / "nyt.json"
    with open(nyt_path, "r") as f:
        return json.load(f)


def test_descriptions_in_inputs():
    """Test that parameter descriptions are preserved in extracted inputs."""
    print("Loading NYT API specification...")
    spec = load_nyt_spec()
    
    print("Extracting operation details for GET /articlesearch.json...")
    result = extract_operation_io(spec, "/articlesearch.json", "get")
    
    # Check if we have inputs
    if "inputs" not in result:
        print("❌ FAIL: No 'inputs' found in result")
        return False
        
    inputs = result["inputs"]
    properties = inputs.get("properties", {})
    
    print(f"Found {len(properties)} input properties")
    
    # Test cases for parameters that should have descriptions
    test_cases = [
        ("q", "Search query term. Search is performed on the article body, headline and byline."),
        ("fq", "Filtered search query using standard Lucene syntax. \n\nThe filter query can be specified with or without a limiting field: label. \n\nSee Filtering Your Search for more information about filtering."),
        ("begin_date", "Format: YYYYMMDD \n\nRestricts responses to results with publication dates of the date specified or later."),
        ("sort", "By default, search results are sorted by their relevance to the query term (q). Use the sort parameter to sort by pub_date."),
        ("hl", "Enables highlighting in search results. When set to true, the query term (q) is highlighted in the headline and lead_paragraph fields.\n\nNote: If highlighting is enabled, snippet will be returned even if it is not specified in your fl list."),
    ]
    
    passed_tests = 0
    total_tests = len(test_cases)
    
    print("\nTesting parameter descriptions:")
    for param_name, expected_description in test_cases:
        if param_name not in properties:
            print(f"❌ FAIL: Parameter '{param_name}' not found in properties")
            continue
            
        param_schema = properties[param_name]
        if "description" not in param_schema:
            print(f"❌ FAIL: Parameter '{param_name}' missing description")
            print(f"   Schema: {param_schema}")
            continue
            
        actual_description = param_schema["description"]
        # Clean up whitespace for comparison
        expected_clean = expected_description.strip().replace('\n', ' ')
        actual_clean = actual_description.strip().replace('\n', ' ')
        
        if expected_clean in actual_clean or actual_clean in expected_clean:
            print(f"✅ PASS: Parameter '{param_name}' has description")
            passed_tests += 1
        else:
            print(f"❌ FAIL: Parameter '{param_name}' description mismatch")
            print(f"   Expected: {expected_description}")
            print(f"   Actual: {actual_description}")
    
    # Show a few examples of what the extracted properties look like
    print(f"\nExample extracted properties:")
    for i, (param_name, param_schema) in enumerate(properties.items()):
        if i >= 3:  # Show first 3 examples
            break
        print(f"  {param_name}: {param_schema}")
    
    print(f"\nTest Results: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("🎉 SUCCESS: All descriptions are properly preserved!")
        return True
    else:
        print("❌ Some tests failed. Descriptions may not be properly preserved.")
        return False


if __name__ == "__main__":
    success = test_descriptions_in_inputs()
    sys.exit(0 if success else 1)