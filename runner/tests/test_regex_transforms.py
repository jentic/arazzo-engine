#!/usr/bin/env python3
"""
Test script for the regex transformation functionality in the Arazzo evaluator.
"""

from arazzo_runner.evaluator import ExpressionEvaluator
from arazzo_runner.models import ExecutionState

def test_regex_transforms():
    """Test the new regex transformation functionality"""
    
    # Create a mock execution state
    state = ExecutionState(workflow_id="test_workflow")
    state.step_outputs = {
        "get-upload-url": {
            "upload_url": "https://example.com/uploads/files/document.pdf"
        }
    }
    
    # Test parameter with x-transform (your example)
    parameter_config = {
        "name": "file_path",
        "in": "path",
        "value": "$steps.get-upload-url.outputs.upload_url",
        "x-transform": [
            {
                "type": "regex",
                "pattern": r".*/(?P<basename>[^/]+)$",
                "result": r"\<basename>",
                "description": "Extract the basename (portion after the last slash) from the upload URL"
            }
        ]
    }
    
    print("Testing regex transformation:")
    print(f"Input URL: {state.step_outputs['get-upload-url']['upload_url']}")
    print(f"Parameter config: {parameter_config}")
    
    # First evaluate the expression, then apply transforms (simplified approach)
    base_value = ExpressionEvaluator.evaluate_expression(parameter_config["value"], state)
    result = ExpressionEvaluator.apply_regex_transforms(base_value, parameter_config["x-transform"])
    
    print(f"Result: {result}")
    print(f"Expected: document.pdf")
    print(f"Success: {result == 'document.pdf'}")
    
    print("\n" + "="*50 + "\n")
    
    # Test multiple transforms in sequence
    multi_transforms = [
        {
            "type": "regex",
            "pattern": r".*/(?P<basename>[^/]+)$",
            "result": r"\<basename>",
            "description": "Extract basename"
        },
        {
            "type": "regex", 
            "pattern": r"(?P<name>.*?)\.(?P<ext>[^.]+)$",
            "result": r"\<name>_processed.\<ext>",
            "description": "Add _processed suffix before extension"
        }
    ]
    
    print("Testing multiple transforms in sequence:")
    print(f"Input URL: {state.step_outputs['get-upload-url']['upload_url']}")
    
    base_value2 = ExpressionEvaluator.evaluate_expression("$steps.get-upload-url.outputs.upload_url", state)
    result2 = ExpressionEvaluator.apply_regex_transforms(base_value2, multi_transforms)
    
    print(f"Result: {result2}")
    print(f"Expected: document_processed.pdf")
    print(f"Success: {result2 == 'document_processed.pdf'}")
    
    print("\n" + "="*50 + "\n")
    
    # Test with numbered backreferences
    numbered_transforms = [
        {
            "type": "regex",
            "pattern": r"https://([^/]+)/([^/]+)/([^/]+)/(.+)",
            "result": r"domain=\1, path1=\2, path2=\3, file=\4",
            "description": "Extract URL components using numbered groups"
        }
    ]
    
    print("Testing numbered backreferences:")
    print(f"Input URL: {state.step_outputs['get-upload-url']['upload_url']}")
    
    base_value3 = ExpressionEvaluator.evaluate_expression("$steps.get-upload-url.outputs.upload_url", state)
    result3 = ExpressionEvaluator.apply_regex_transforms(base_value3, numbered_transforms)
    
    print(f"Result: {result3}")
    print(f"Expected: domain=example.com, path1=uploads, path2=files, file=document.pdf")
    expected3 = "domain=example.com, path1=uploads, path2=files, file=document.pdf"
    print(f"Success: {result3 == expected3}")
    
    print("\n" + "="*50 + "\n")
    
    # Test escaped literals (\\1 -> literal \1)
    escaped_transforms = [
        {
            "type": "regex",
            "pattern": r"https://([^/]+)/([^/]+)/([^/]+)/(.+)",
            "result": r"Domain: \1, Literal: \\1, File: \4",
            "description": "Test escaped literals - \\1 should become literal \\1"
        }
    ]
    
    print("Testing escaped literals (\\\\1 -> \\1):")
    print(f"Input URL: {state.step_outputs['get-upload-url']['upload_url']}")
    
    base_value4 = ExpressionEvaluator.evaluate_expression("$steps.get-upload-url.outputs.upload_url", state)
    result4 = ExpressionEvaluator.apply_regex_transforms(base_value4, escaped_transforms)
    
    print(f"Result: {result4}")
    print(f"Expected: Domain: example.com, Literal: \\1, File: document.pdf")
    expected4 = "Domain: example.com, Literal: \\1, File: document.pdf"
    print(f"Success: {result4 == expected4}")
    
    print("\n" + "="*50 + "\n")
    
    # Test escaped named groups (\\<name> -> literal \<name>)
    escaped_named_transforms = [
        {
            "type": "regex",
            "pattern": r".*/(?P<basename>[^/]+)$",
            "result": r"File: \<basename>, Literal: \\<basename>",
            "description": "Test escaped named groups - \\<basename> should become literal \\<basename>"
        }
    ]
    
    print("Testing escaped named groups (\\\\<basename> -> \\<basename>):")
    print(f"Input URL: {state.step_outputs['get-upload-url']['upload_url']}")
    
    base_value5 = ExpressionEvaluator.evaluate_expression("$steps.get-upload-url.outputs.upload_url", state)
    result5 = ExpressionEvaluator.apply_regex_transforms(base_value5, escaped_named_transforms)
    
    print(f"Result: {result5}")
    print(f"Expected: File: document.pdf, Literal: \\<basename>")
    expected5 = "File: document.pdf, Literal: \\<basename>"
    print(f"Success: {result5 == expected5}")

if __name__ == "__main__":
    test_regex_transforms()
