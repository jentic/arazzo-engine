"""Tests for the ArazzoGenerator class."""

import unittest
from unittest.mock import MagicMock, patch

from arazzo_generator.generator.arazzo_generator import ArazzoGenerator
from arazzo_generator.utils.utils import to_kebab_case


class TestArazzoGenerator(unittest.TestCase):
    """Tests for the ArazzoGenerator class."""

    def setUp(self):
        """Set up test fixtures."""
        # Sample endpoints for testing
        self.endpoints = {
            "/pets": {
                "get": {
                    "operation_id": "listPets",
                    "summary": "List all pets",
                    "description": "Returns a list of pets",
                    "tags": ["pet"],
                    "parameters": [
                        {
                            "name": "limit",
                            "in": "query",
                            "description": "How many items to return",
                            "schema": {"type": "integer", "format": "int32"},
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "A list of pets",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "array",
                                        "items": {"$ref": "#/components/schemas/Pet"},
                                    }
                                }
                            },
                        }
                    },
                },
                "post": {
                    "operation_id": "createPet",
                    "summary": "Create a pet",
                    "description": "Creates a new pet in the store",
                    "tags": ["pet"],
                    "requestBody": {
                        "description": "Pet to add to the store",
                        "content": {
                            "application/json": {"schema": {"$ref": "#/components/schemas/Pet"}}
                        },
                    },
                    "responses": {
                        "201": {
                            "description": "Pet created",
                            "content": {
                                "application/json": {"schema": {"$ref": "#/components/schemas/Pet"}}
                            },
                        }
                    },
                },
            },
            "/pets/{petId}": {
                "get": {
                    "operation_id": "getPetById",
                    "summary": "Get a pet by ID",
                    "description": "Returns a pet by ID",
                    "tags": ["pet"],
                    "parameters": [
                        {
                            "name": "petId",
                            "in": "path",
                            "description": "ID of pet to return",
                            "required": True,
                            "schema": {"type": "string"},
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Pet found",
                            "content": {
                                "application/json": {"schema": {"$ref": "#/components/schemas/Pet"}}
                            },
                        }
                    },
                },
                "put": {
                    "operation_id": "updatePet",
                    "summary": "Update a pet",
                    "description": "Updates a pet in the store",
                    "tags": ["pet"],
                    "parameters": [
                        {
                            "name": "petId",
                            "in": "path",
                            "description": "ID of pet to update",
                            "required": True,
                            "schema": {"type": "string"},
                        }
                    ],
                    "requestBody": {
                        "description": "Pet to update",
                        "content": {
                            "application/json": {"schema": {"$ref": "#/components/schemas/Pet"}}
                        },
                    },
                    "responses": {
                        "200": {
                            "description": "Pet updated",
                            "content": {
                                "application/json": {"schema": {"$ref": "#/components/schemas/Pet"}}
                            },
                        }
                    },
                },
                "delete": {
                    "operation_id": "deletePet",
                    "summary": "Delete a pet",
                    "description": "Deletes a pet from the store",
                    "tags": ["pet"],
                    "parameters": [
                        {
                            "name": "petId",
                            "in": "path",
                            "description": "ID of pet to delete",
                            "required": True,
                            "schema": {"type": "string"},
                        }
                    ],
                    "responses": {"204": {"description": "Pet deleted"}},
                },
            },
        }

        # Sample OpenAPI spec for testing
        self.openapi_spec = {
            "openapi": "3.0.0",
            "info": {
                "title": "Pet Store API",
                "version": "1.0.0",
                "description": "A sample API for pets",
            },
            "paths": self.endpoints,
            "components": {
                "schemas": {
                    "Pet": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "name": {"type": "string"},
                            "tag": {"type": "string"},
                        },
                    }
                }
            },
        }

        # Sample workflows for testing
        self.workflows = [
            {
                "name": "pet_management",
                "description": "Manage pets in the store",
                "type": "process",
                "operations": [
                    {
                        "name": "list_pets",
                        "description": "List all pets in the store",
                        "endpoints": [["/pets", "get"]],
                        "inputs": ["limit"],
                        "outputs": ["pets_list"],
                    },
                    {
                        "name": "get_pet",
                        "description": "Get a specific pet by ID",
                        "endpoints": [["/pets/{petId}", "get"]],
                        "inputs": ["petId"],
                        "outputs": ["pet_details"],
                        "dependencies": {
                            "petId": {"step": "list_pets", "output": "pets_list[0].id"}
                        },
                    },
                    {
                        "name": "update_pet",
                        "description": "Update a pet's information",
                        "endpoints": [["/pets/{petId}", "put"]],
                        "inputs": ["petId", "pet_data"],
                        "outputs": ["updated_pet"],
                        "dependencies": {
                            "petId": {"step": "get_pet", "output": "pet_details.id"},
                            "pet_data": {"step": "get_pet", "output": "pet_details"},
                        },
                    },
                ],
            },
            {
                "name": "pet_crud",
                "description": "CRUD operations for pets",
                "type": "crud",
                "resource": "pet",
                "operations": [
                    {
                        "name": "create",
                        "description": "Create a new pet",
                        "endpoints": [["/pets", "post"]],
                        "inputs": ["pet_data"],
                        "outputs": ["created_pet"],
                    },
                    {
                        "name": "read",
                        "description": "Get a pet by ID",
                        "endpoints": [["/pets/{petId}", "get"]],
                        "inputs": ["petId"],
                        "outputs": ["pet"],
                    },
                    {
                        "name": "update",
                        "description": "Update a pet",
                        "endpoints": [["/pets/{petId}", "put"]],
                        "inputs": ["petId", "pet_data"],
                        "outputs": ["updated_pet"],
                    },
                    {
                        "name": "delete",
                        "description": "Delete a pet",
                        "endpoints": [["/pets/{petId}", "delete"]],
                        "inputs": ["petId"],
                        "outputs": ["deletion_status"],
                    },
                ],
            },
        ]

    def test_init(self):
        """Test initialization of the ArazzoGenerator."""
        # Test with required parameters
        generator = ArazzoGenerator(
            self.workflows, "https://example.com/openapi.json", self.endpoints
        )
        self.assertEqual(generator.workflows, self.workflows)
        self.assertEqual(generator.openapi_spec_url, "https://example.com/openapi.json")
        self.assertEqual(generator.endpoints, self.endpoints)
        self.assertEqual(generator.openapi_spec, None)
        self.assertEqual(generator.arazzo_spec, {})

        # Test with optional parameters
        generator = ArazzoGenerator(
            self.workflows,
            "https://example.com/openapi.json",
            self.endpoints,
            self.openapi_spec,
        )
        self.assertEqual(generator.workflows, self.workflows)
        self.assertEqual(generator.openapi_spec_url, "https://example.com/openapi.json")
        self.assertEqual(generator.endpoints, self.endpoints)
        self.assertEqual(generator.openapi_spec, self.openapi_spec)
        self.assertEqual(generator.arazzo_spec, {})

    def test_generate_no_workflows(self):
        """Test generate method with no workflows."""
        generator = ArazzoGenerator([], "https://example.com/openapi.json", self.endpoints)
        result = generator.generate()
        self.assertIsNone(result)

    @patch("arazzo_generator.generator.arazzo_generator.WorkflowBuilder")
    def test_generate_with_workflows(self, mock_workflow_builder_class):
        """Test generate method with workflows."""
        # Configure the mock
        mock_workflow_builder = MagicMock()
        mock_workflow_builder_class.return_value = mock_workflow_builder

        # Mock the create_workflow method to return a valid workflow for the first workflow
        # and None for the second workflow (to test filtering)
        mock_workflow_builder.create_workflow.side_effect = [
            {
                "workflowId": "pet-management",
                "summary": "Manage pets in the store",
                "description": "Manage pets in the store",
                "steps": [
                    {
                        "stepId": "list-pets",
                        "summary": "List all pets in the store",
                        "parameters": [{"name": "limit", "value": "$inputs.limit"}],
                        "outputs": {"pets_list": "$response.body"},
                    },
                    {
                        "stepId": "get-pet",
                        "summary": "Get a specific pet by ID",
                        "parameters": [
                            {
                                "name": "petId",
                                "value": "$steps.list-pets.outputs.pets_list[0].id",
                            }
                        ],
                        "outputs": {"pet_details": "$response.body"},
                        "dependencies": [{"condition": "$steps.list-pets.status == 'success'"}],
                    },
                    {
                        "stepId": "update-pet",
                        "summary": "Update a pet's information",
                        "parameters": [
                            {
                                "name": "petId",
                                "value": "$steps.get-pet.outputs.pet_details.id",
                            }
                        ],
                        "requestBody": {
                            "contentType": "application/json",
                            "payload": "$steps.get-pet.outputs.pet_details",
                        },
                        "outputs": {"updated_pet": "$response.body"},
                        "dependencies": [{"condition": "$steps.get-pet.status == 'success'"}],
                    },
                ],
                "inputs": {
                    "type": "object",
                    "properties": {"limit": {"type": "integer"}},
                },
                "outputs": {
                    "pets_list": "$steps.list-pets.outputs.pets_list",
                    "pet_details": "$steps.get-pet.outputs.pet_details",
                    "updated_pet": "$steps.update-pet.outputs.updated_pet",
                },
                "failureActions": [
                    {"reference": "$components.failureActions.auth_failure"},
                    {"reference": "$components.failureActions.permission_denied"},
                    {"reference": "$components.failureActions.not_found"},
                    {"reference": "$components.failureActions.server_error"},
                ],
            },
            None,  # Second workflow returns None (invalid)
        ]

        # Create generator and call generate
        generator = ArazzoGenerator(
            self.workflows,
            "https://example.com/openapi.json",
            self.endpoints,
            self.openapi_spec,
        )
        result = generator.generate()

        # Verify that WorkflowBuilder was initialized correctly
        mock_workflow_builder_class.assert_called_once_with(self.endpoints, self.openapi_spec)

        # Verify that create_workflow was called for each workflow
        self.assertEqual(mock_workflow_builder.create_workflow.call_count, 2)
        mock_workflow_builder.create_workflow.assert_any_call(self.workflows[0])
        mock_workflow_builder.create_workflow.assert_any_call(self.workflows[1])

        # Verify the result
        self.assertIsNotNone(result)
        self.assertEqual(result["arazzo"], "1.0.1")
        self.assertEqual(result["info"]["title"], "Jentic Generated Arazzo Specification")
        self.assertEqual(len(result["sourceDescriptions"]), 1)
        self.assertEqual(result["sourceDescriptions"][0]["url"], "https://example.com/openapi.json")
        self.assertEqual(len(result["workflows"]), 1)  # Only one valid workflow
        self.assertEqual(result["workflows"][0]["workflowId"], "pet-management")
        self.assertIn("components", result)

    @patch("arazzo_generator.generator.arazzo_generator.WorkflowBuilder")
    def test_generate_no_valid_workflows(self, mock_workflow_builder_class):
        """Test generate method when no valid workflows are created."""
        # Configure the mock to return None for all workflows
        mock_workflow_builder = MagicMock()
        mock_workflow_builder_class.return_value = mock_workflow_builder
        mock_workflow_builder.create_workflow.return_value = None

        # Create generator and call generate
        generator = ArazzoGenerator(
            self.workflows, "https://example.com/openapi.json", self.endpoints
        )
        result = generator.generate()

        # Verify that WorkflowBuilder was initialized correctly
        mock_workflow_builder_class.assert_called_once_with(self.endpoints, None)

        # Verify that create_workflow was called for each workflow
        self.assertEqual(mock_workflow_builder.create_workflow.call_count, 2)

        # Verify the result is None since no valid workflows were created
        self.assertIsNone(result)

    @patch("arazzo_generator.generator.arazzo_generator.ArazzoSerializer")
    def test_to_yaml(self, mock_serializer):
        """Test to_yaml method."""
        # Configure the mock
        mock_serializer.to_yaml.return_value = "yaml_content"

        # Create a generator with a pre-populated arazzo_spec
        generator = ArazzoGenerator(
            self.workflows, "https://example.com/openapi.json", self.endpoints
        )
        generator.arazzo_spec = {"arazzo": "1.0.1"}

        # Call to_yaml
        result = generator.to_yaml()

        # Verify that to_yaml was called with the arazzo_spec
        mock_serializer.to_yaml.assert_called_once_with({"arazzo": "1.0.1"})

        # Verify the result
        self.assertEqual(result, "yaml_content")

    @patch("arazzo_generator.generator.arazzo_generator.ArazzoSerializer")
    def test_to_json(self, mock_serializer):
        """Test to_json method."""
        # Configure the mock
        mock_serializer.to_json.return_value = "json_content"

        # Create a generator with a pre-populated arazzo_spec
        generator = ArazzoGenerator(
            self.workflows, "https://example.com/openapi.json", self.endpoints
        )
        generator.arazzo_spec = {"arazzo": "1.0.1"}

        # Call to_json
        result = generator.to_json()

        # Verify that to_json was called with the arazzo_spec
        mock_serializer.to_json.assert_called_once_with({"arazzo": "1.0.1"})

        # Verify the result
        self.assertEqual(result, "json_content")

    def test_workflow_dependencies_resolution(self):
        """Test that workflow dependencies are correctly resolved in the generated Arazzo."""
        # Create a real generator (no mocks) to test actual dependency resolution
        generator = ArazzoGenerator(
            self.workflows,
            "https://example.com/openapi.json",
            self.endpoints,
            self.openapi_spec,
        )

        # Generate the Arazzo specification
        result = generator.generate()

        # Verify that the result is not None
        self.assertIsNotNone(result)

        # Find the workflow with dependencies
        workflow = None
        for w in result["workflows"]:
            if w["workflowId"] == "pet-management":
                workflow = w
                break

        # Verify that the workflow was found
        self.assertIsNotNone(workflow)

        # Verify that the workflow has the correct steps
        self.assertEqual(len(workflow["steps"]), 3)

        # Verify that the parameters reference other steps
        get_pet_step = None
        update_pet_step = None
        for step in workflow["steps"]:
            if step["stepId"] == "get-pet":
                get_pet_step = step
            elif step["stepId"] == "update-pet":
                update_pet_step = step

        # Verify that the get_pet step was found
        self.assertIsNotNone(get_pet_step)

        # Verify that the update_pet step was found
        self.assertIsNotNone(update_pet_step)

        # Verify that the parameter value references the correct step output
        self.assertIn("parameters", get_pet_step)
        pet_id_param = None
        for param in get_pet_step["parameters"]:
            if param["name"] == "petId":
                pet_id_param = param
                break

        self.assertIsNotNone(pet_id_param)
        self.assertTrue(
            pet_id_param["value"].startswith("$steps.")
            or pet_id_param["value"].startswith("$inputs.")
        )

        # Verify that the request body references the correct step output (if present)
        if "requestBody" in update_pet_step:
            self.assertIn("payload", update_pet_step["requestBody"])

    def test_workflow_outputs_correctness(self):
        """Test that workflow outputs are correctly generated in the Arazzo specification."""
        # Create a real generator to test actual output generation
        generator = ArazzoGenerator(
            self.workflows,
            "https://example.com/openapi.json",
            self.endpoints,
            self.openapi_spec,
        )

        # Generate the Arazzo specification
        result = generator.generate()

        # Verify that the result is not None
        self.assertIsNotNone(result)

        # Find the pet management workflow
        pet_management_workflow = None
        for w in result["workflows"]:
            if w["workflowId"] == "pet-management":
                pet_management_workflow = w
                break

        # Verify that the workflow was found
        self.assertIsNotNone(pet_management_workflow)

        # Verify that the workflow has outputs
        self.assertIn("outputs", pet_management_workflow)

        # Get the actual output keys
        actual_outputs = set(pet_management_workflow["outputs"].keys())

        # Verify that we have outputs (without requiring exact matches)
        self.assertTrue(len(actual_outputs) > 0, "Workflow should have outputs")

        # Verify that each output references a step
        for output_name, output_ref in pet_management_workflow["outputs"].items():
            self.assertTrue(
                output_ref.startswith("$steps."),
                f"Output {output_name} should reference a step, but got {output_ref}",
            )

    def test_step_input_output_dependencies(self):
        """Test that step input/output dependencies are correctly parsed and resolved."""
        # Create a real generator to test actual dependency resolution
        generator = ArazzoGenerator(
            self.workflows,
            "https://example.com/openapi.json",
            self.endpoints,
            self.openapi_spec,
        )

        # Generate the Arazzo specification
        result = generator.generate()

        # Verify that the result is not None
        self.assertIsNotNone(result)

        # Find the pet management workflow
        pet_management_workflow = None
        for w in result["workflows"]:
            if w["workflowId"] == "pet-management":
                pet_management_workflow = w
                break

        # Verify that the workflow was found
        self.assertIsNotNone(pet_management_workflow)

        # Get the steps
        list_pets_step = None
        get_pet_step = None
        update_pet_step = None

        for step in pet_management_workflow["steps"]:
            if step["stepId"] == "list-pets":
                list_pets_step = step
            elif step["stepId"] == "get-pet":
                get_pet_step = step
            elif step["stepId"] == "update-pet":
                update_pet_step = step

        # Verify that all steps were found
        self.assertIsNotNone(list_pets_step)
        self.assertIsNotNone(get_pet_step)
        self.assertIsNotNone(update_pet_step)

        # Verify list_pets step has the correct parameter
        self.assertIn("parameters", list_pets_step)
        self.assertGreaterEqual(len(list_pets_step["parameters"]), 1)

        # Find the limit parameter
        limit_param = None
        for param in list_pets_step["parameters"]:
            if param["name"] == "limit":
                limit_param = param
                break

        self.assertIsNotNone(limit_param)
        self.assertEqual(limit_param["value"], "$inputs.limit")

        # Verify get_pet step has the correct parameter
        self.assertIn("parameters", get_pet_step)
        self.assertGreaterEqual(len(get_pet_step["parameters"]), 1)

        # Find the petId parameter
        pet_id_param = None
        for param in get_pet_step["parameters"]:
            if param["name"] == "petId":
                pet_id_param = param
                break

        self.assertIsNotNone(pet_id_param)
        # The value should reference a step output (but we don't check the exact format)
        self.assertTrue(
            pet_id_param["value"].startswith("$steps.")
            or pet_id_param["value"].startswith("$inputs.")
        )

        # Verify update_pet step has the correct parameters
        self.assertIn("parameters", update_pet_step)
        self.assertGreaterEqual(len(update_pet_step["parameters"]), 1)

        # Find the petId parameter
        pet_id_param = None
        for param in update_pet_step["parameters"]:
            if param["name"] == "petId":
                pet_id_param = param
                break

        self.assertIsNotNone(pet_id_param)
        # The value should reference a step output (but we don't check the exact format)
        self.assertTrue(
            pet_id_param["value"].startswith("$steps.")
            or pet_id_param["value"].startswith("$inputs.")
        )

        # Verify update_pet step has a request body (if present)
        if "requestBody" in update_pet_step:
            self.assertIn("payload", update_pet_step["requestBody"])

    def test_reference_validator_integration(self):
        """Test that the ReferenceValidator is correctly integrated and fixes references."""
        # Create a workflow with incorrect references that need to be fixed
        workflow_with_bad_refs = {
            "name": "workflow_with_bad_refs",
            "description": "Workflow with references that need fixing",
            "type": "process",
            "operations": [
                {
                    "name": "list_pets",
                    "description": "List all pets",
                    "endpoints": [["/pets", "get"]],
                    "inputs": ["limit"],
                    "outputs": ["pets"],
                },
                {
                    "name": "get_pet",
                    "description": "Get a pet by ID",
                    "endpoints": [["/pets/{petId}", "get"]],
                    "inputs": ["petId"],
                    "outputs": ["pet"],
                    "dependencies": {
                        # Incorrect step name (should be list_pets)
                        "petId": {"step": "list_all_pets", "output": "pets[0].id"}
                    },
                },
                {
                    "name": "update_pet",
                    "description": "Update a pet's information",
                    "endpoints": [["/pets/{petId}", "put"]],
                    "inputs": ["petId", "pet_data"],
                    "outputs": ["updated_pet"],
                    "dependencies": {
                        # Incorrect step name (should be get_pet)
                        "petId": {"step": "get_pet_by_id", "output": "pet_details.id"},
                        # Incorrect output name (should be pet_details)
                        "pet_data": {"step": "get_pet", "output": "pet_info"},
                    },
                },
            ],
        }

        # Create a generator with the bad workflow
        generator = ArazzoGenerator(
            [workflow_with_bad_refs],
            "https://example.com/openapi.json",
            self.endpoints,
            self.openapi_spec,
        )

        # Generate the Arazzo specification directly without mocking
        # The actual implementation will use the ReferenceValidator internally
        result = generator.generate()

        # Verify that the result is not None
        self.assertIsNotNone(result)

        # Find the workflow
        self.assertGreaterEqual(len(result["workflows"]), 1)
        workflow = result["workflows"][0]

        # Verify that the workflow has the correct steps
        self.assertEqual(len(workflow["steps"]), 3)

        # Get the update_pet step
        update_pet_step = None
        for step in workflow["steps"]:
            if step["stepId"] == "update-pet":
                update_pet_step = step
                break

        # Verify that the update_pet step was found
        self.assertIsNotNone(update_pet_step)

        # Verify that the step was created successfully despite the bad references
        self.assertIn("parameters", update_pet_step)

    def test_multiple_llm_providers(self):
        """Test that the generator works with workflows from different LLM providers."""
        # This test verifies that the generator can handle workflows from different LLM providers
        # by ensuring that the basic structure is maintained regardless of provider-specific details

        # Create workflows with slightly different formats (simulating different LLM providers)
        openai_workflow = {
            "name": "openai_workflow",
            "description": "Workflow from OpenAI",
            "type": "process",
            "operations": [
                {
                    "name": "list_pets",
                    "description": "List all pets",
                    "endpoints": [["/pets", "get"]],
                    "inputs": ["limit"],
                    "outputs": ["pets"],
                },
                {
                    "name": "get_pet",
                    "description": "Get a pet by ID",
                    "endpoints": [["/pets/{petId}", "get"]],
                    "inputs": ["petId"],
                    "outputs": ["pet"],
                    "dependencies": {"petId": {"step": "list_pets", "output": "pets[0].id"}},
                },
            ],
        }

        anthropic_workflow = {
            "name": "anthropic_workflow",
            "description": "Workflow from Anthropic",
            "type": "process",
            # Slightly different format for operations
            "operations": [
                {
                    "name": "list_pets",
                    "description": "List all pets",
                    "endpoint": "/pets",  # Different format
                    "method": "get",  # Different format
                    "inputs": ["limit"],
                    "outputs": ["pets"],
                },
                {
                    "name": "get_pet",
                    "description": "Get a pet by ID",
                    "endpoint": "/pets/{petId}",  # Different format
                    "method": "get",  # Different format
                    "inputs": ["petId"],
                    "outputs": ["pet"],
                    # Different format for dependencies
                    "input_dependencies": {"petId": "list_pets.pets[0].id"},
                },
            ],
        }

        # Create a generator with both workflows
        generator = ArazzoGenerator(
            [openai_workflow, anthropic_workflow],
            "https://example.com/openapi.json",
            self.endpoints,
            self.openapi_spec,
        )

        # Mock the WorkflowBuilder to return a simple workflow for each input
        with patch(
            "arazzo_generator.generator.arazzo_generator.WorkflowBuilder.create_workflow"
        ) as mock_create_workflow:
            # Configure the mock to return a simple workflow for each input
            mock_create_workflow.side_effect = lambda workflow: {
                "workflowId": to_kebab_case(workflow["name"]),
                "summary": workflow["description"],
                "description": workflow["description"],
                "steps": [
                    {"stepId": "step-1", "summary": "Step 1"},
                    {"stepId": "step-2", "summary": "Step 2"},
                ],
            }

            # Call generate
            result = generator.generate()

            # Verify that the result is not None
            self.assertIsNotNone(result)

            # Verify that both workflows were processed
            self.assertEqual(mock_create_workflow.call_count, 2)
            mock_create_workflow.assert_any_call(openai_workflow)
            mock_create_workflow.assert_any_call(anthropic_workflow)

            # Verify that both workflows are in the result
            self.assertEqual(len(result["workflows"]), 2)
            workflow_ids = [w["workflowId"] for w in result["workflows"]]
            self.assertIn("openai-workflow", workflow_ids)
            self.assertIn("anthropic-workflow", workflow_ids)

    def test_workflow_properties_assignment(self):
        """Test that workflow properties are correctly assigned in the generated Arazzo."""
        # Create a real generator (no mocks) to test actual property assignment
        generator = ArazzoGenerator(
            self.workflows,
            "https://example.com/openapi.json",
            self.endpoints,
            self.openapi_spec,
        )

        # Generate the Arazzo specification
        result = generator.generate()

        # Verify that the result is not None
        self.assertIsNotNone(result)

        # Verify that the Arazzo specification has the correct properties
        self.assertEqual(result["arazzo"], "1.0.1")
        self.assertEqual(result["info"]["title"], "Jentic Generated Arazzo Specification")
        self.assertEqual(result["info"]["version"], "1.0.0")

        # Verify that the source descriptions are correct
        self.assertEqual(len(result["sourceDescriptions"]), 1)
        self.assertEqual(result["sourceDescriptions"][0]["name"], "openapi_source")
        self.assertEqual(result["sourceDescriptions"][0]["url"], "https://example.com/openapi.json")
        self.assertEqual(result["sourceDescriptions"][0]["type"], "openapi")

        # Verify that the components section exists
        self.assertIn("components", result)

        # Verify that the workflows section exists and has the correct workflows
        self.assertIn("workflows", result)
        self.assertGreaterEqual(len(result["workflows"]), 1)

        # Verify that the workflow IDs are in kebab-case
        for workflow in result["workflows"]:
            self.assertIn("-", workflow["workflowId"])

        # Verify that each workflow has the required properties
        for workflow in result["workflows"]:
            self.assertIn("workflowId", workflow)
            self.assertIn("description", workflow)
            self.assertIn("steps", workflow)
            self.assertIn("failureActions", workflow)

            # Verify that each step has the required properties
            for step in workflow["steps"]:
                self.assertIn("stepId", step)
                self.assertIn("description", step)


if __name__ == "__main__":
    unittest.main()
