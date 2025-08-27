"""Tests for the WorkflowBuilder class."""

import unittest
from unittest.mock import patch

from arazzo_generator.generator.workflow_builder import WorkflowBuilder
from arazzo_generator.utils.utils import to_kebab_case


class TestWorkflowBuilder(unittest.TestCase):
    """Tests for the WorkflowBuilder class."""

    def setUp(self):
        """Set up test fixtures."""
        # Sample identified workflow
        self.identified_workflow = {
            "name": "Pet Management",
            "description": "Manage pets in the pet store",
            "steps": [
                {
                    "id": "list-pets",
                    "description": "List all pets",
                    "operation": {
                        "operationId": "listPets",
                        "path": "/pets",
                        "method": "get",
                    },
                    "outputs": {
                        "pets_list": "$response.body",
                        "count": "$response.body.length",
                    },
                },
                {
                    "id": "get-pet",
                    "description": "Get a specific pet",
                    "operation": {
                        "operationId": "getPetById",
                        "path": "/pets/{petId}",
                        "method": "get",
                    },
                    "parameters": [
                        {
                            "name": "petId",
                            "value": "$steps.list-pets.outputs.pets_list[0].id",
                        }
                    ],
                    "outputs": {"pet_details": "$response.body"},
                },
            ],
        }

        # Sample OpenAPI spec
        self.openapi_spec = {
            "paths": {
                "/pets": {
                    "get": {
                        "operationId": "listPets",
                        "summary": "List all pets",
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
                    }
                },
                "/pets/{petId}": {
                    "get": {
                        "operationId": "getPetById",
                        "summary": "Get a pet by ID",
                        "parameters": [
                            {
                                "name": "petId",
                                "in": "path",
                                "required": True,
                                "schema": {"type": "string"},
                            }
                        ],
                        "responses": {
                            "200": {
                                "description": "A pet",
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/Pet"}
                                    }
                                },
                            }
                        },
                    },
                    "put": {
                        "operationId": "updatePet",
                        "summary": "Update a pet",
                        "parameters": [
                            {
                                "name": "petId",
                                "in": "path",
                                "required": True,
                                "schema": {"type": "string"},
                            }
                        ],
                        "requestBody": {
                            "content": {
                                "application/json": {"schema": {"$ref": "#/components/schemas/Pet"}}
                            }
                        },
                        "responses": {
                            "200": {
                                "description": "Updated pet",
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/Pet"}
                                    }
                                },
                            }
                        },
                    },
                },
            },
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

        # Create endpoints dictionary from OpenAPI spec
        self.endpoints = {
            "listPets": {
                "path": "/pets",
                "method": "get",
                "summary": "List all pets",
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
            "getPetById": {
                "path": "/pets/{petId}",
                "method": "get",
                "summary": "Get a pet by ID",
                "parameters": [
                    {
                        "name": "petId",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                ],
                "responses": {
                    "200": {
                        "description": "A pet",
                        "content": {
                            "application/json": {"schema": {"$ref": "#/components/schemas/Pet"}}
                        },
                    }
                },
            },
            "updatePet": {
                "path": "/pets/{petId}",
                "method": "put",
                "summary": "Update a pet",
                "parameters": [
                    {
                        "name": "petId",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                ],
                "requestBody": {
                    "content": {
                        "application/json": {"schema": {"$ref": "#/components/schemas/Pet"}}
                    }
                },
                "responses": {
                    "200": {
                        "description": "Updated pet",
                        "content": {
                            "application/json": {"schema": {"$ref": "#/components/schemas/Pet"}}
                        },
                    }
                },
            },
        }

        # Create a WorkflowBuilder instance with the correct parameters
        self.workflow_builder = WorkflowBuilder(
            endpoints=self.endpoints, openapi_spec=self.openapi_spec
        )

    def test_init(self):
        """Test the initialization of the WorkflowBuilder."""
        self.assertEqual(self.workflow_builder.endpoints, self.endpoints)
        self.assertEqual(self.workflow_builder.openapi_spec, self.openapi_spec)

    def test_create_workflow(self):
        """Test the create_workflow method."""
        # Create a workflow from the identified workflow
        with patch.object(self.workflow_builder, "_create_steps") as mock_create_steps:
            # Mock the _create_steps method to add steps to the steps list
            def side_effect(workflow, temp_workflow):
                temp_workflow["steps"].append(
                    {
                        "stepId": "list-pets",
                        "description": "List all pets",
                        "operation": {
                            "operationId": "listPets",
                            "path": "/pets",
                            "method": "get",
                        },
                        "outputs": {
                            "pets_list": "$response.body",
                            "count": "$response.body.length",
                        },
                    }
                )
                temp_workflow["steps"].append(
                    {
                        "stepId": "get-pet",
                        "description": "Get a specific pet",
                        "operation": {
                            "operationId": "getPetById",
                            "path": "/pets/{petId}",
                            "method": "get",
                        },
                        "parameters": [
                            {
                                "name": "petId",
                                "value": "$steps.list-pets.outputs.pets_list[0].id",
                            }
                        ],
                        "outputs": {"pet_details": "$response.body"},
                    }
                )

            mock_create_steps.side_effect = side_effect

            workflow = self.workflow_builder.create_workflow(self.identified_workflow)

            # Verify the workflow properties
            self.assertEqual(
                workflow["workflowId"], to_kebab_case(self.identified_workflow["name"])
            )
            self.assertEqual(workflow["description"], self.identified_workflow["description"])
            self.assertEqual(len(workflow["steps"]), 2)
            self.assertEqual(workflow["steps"][0]["stepId"], "list-pets")
            self.assertEqual(workflow["steps"][1]["stepId"], "get-pet")

    def test_create_workflow_with_empty_steps(self):
        """Test the create_workflow method with empty steps."""
        # Create a workflow with empty steps
        workflow_with_empty_steps = {
            "name": "Empty Workflow",
            "description": "A workflow with no steps",
            "steps": [],
        }

        # Create a workflow from the identified workflow
        workflow = self.workflow_builder.create_workflow(workflow_with_empty_steps)

        # Verify that the workflow is None (as it has no steps)
        self.assertIsNone(workflow)

    def test_create_workflow_with_failure_action(self):
        """Test the create_workflow method with a failure action."""
        # Create a workflow from the identified workflow
        with patch.object(self.workflow_builder, "_create_steps") as mock_create_steps:
            # Mock the _create_steps method to add steps to the steps list
            def side_effect(workflow, temp_workflow):
                temp_workflow["steps"].append(
                    {
                        "stepId": "list-pets",
                        "description": "List all pets",
                        "operation": {
                            "operationId": "listPets",
                            "path": "/pets",
                            "method": "get",
                        },
                        "outputs": {
                            "pets_list": "$response.body",
                            "count": "$response.body.length",
                        },
                    }
                )
                temp_workflow["steps"].append(
                    {
                        "stepId": "get-pet",
                        "description": "Get a specific pet",
                        "operation": {
                            "operationId": "getPetById",
                            "path": "/pets/{petId}",
                            "method": "get",
                        },
                        "parameters": [
                            {
                                "name": "petId",
                                "value": "$steps.list-pets.outputs.pets_list[0].id",
                            }
                        ],
                        "outputs": {"pet_details": "$response.body"},
                        "failureActions": [{"reference": "$components.failureActions.not_found"}],
                    }
                )

            mock_create_steps.side_effect = side_effect

            workflow = self.workflow_builder.create_workflow(self.identified_workflow)

            # Verify the workflow properties
            self.assertEqual(
                workflow["workflowId"], to_kebab_case(self.identified_workflow["name"])
            )
            self.assertEqual(workflow["description"], self.identified_workflow["description"])
            self.assertEqual(len(workflow["steps"]), 2)
            self.assertEqual(workflow["steps"][0]["stepId"], "list-pets")
            self.assertEqual(workflow["steps"][1]["stepId"], "get-pet")
            self.assertIn("failureActions", workflow)

    def test_create_workflow_with_request_body(self):
        """Test the create_workflow method with a step that has a request body."""
        # Add a step with a request body to the identified workflow
        with patch.object(self.workflow_builder, "_create_steps") as mock_create_steps:
            # Mock the _create_steps method to add steps to the steps list
            def side_effect(workflow, temp_workflow):
                temp_workflow["steps"].append(
                    {
                        "stepId": "list-pets",
                        "description": "List all pets",
                        "operation": {
                            "operationId": "listPets",
                            "path": "/pets",
                            "method": "get",
                        },
                        "outputs": {
                            "pets_list": "$response.body",
                            "count": "$response.body.length",
                        },
                    }
                )
                temp_workflow["steps"].append(
                    {
                        "stepId": "get-pet",
                        "description": "Get a specific pet",
                        "operation": {
                            "operationId": "getPetById",
                            "path": "/pets/{petId}",
                            "method": "get",
                        },
                        "parameters": [
                            {
                                "name": "petId",
                                "value": "$steps.list-pets.outputs.pets_list[0].id",
                            }
                        ],
                        "outputs": {"pet_details": "$response.body"},
                    }
                )
                temp_workflow["steps"].append(
                    {
                        "stepId": "update-pet",
                        "description": "Update a pet",
                        "operation": {
                            "operationId": "updatePet",
                            "path": "/pets/{petId}",
                            "method": "put",
                        },
                        "parameters": [
                            {
                                "name": "petId",
                                "value": "$steps.get-pet.outputs.pet_details.id",
                            }
                        ],
                        "requestBody": {
                            "contentType": "application/json",
                            "payload": {
                                "name": "Updated Pet Name",
                                "tag": "$steps.get-pet.outputs.pet_details.tag",
                            },
                        },
                        "outputs": {"updated_pet": "$response.body"},
                    }
                )

            mock_create_steps.side_effect = side_effect

            workflow = self.workflow_builder.create_workflow(self.identified_workflow)

            # Verify the request body
            self.assertEqual(workflow["steps"][2]["requestBody"]["contentType"], "application/json")
            self.assertEqual(
                workflow["steps"][2]["requestBody"]["payload"]["name"],
                "Updated Pet Name",
            )
            self.assertEqual(
                workflow["steps"][2]["requestBody"]["payload"]["tag"],
                "$steps.get-pet.outputs.pet_details.tag",
            )

    def test_create_workflow_with_multiple_llm_providers(self):
        """Test the create_workflow method with different LLM providers."""
        # Create a WorkflowBuilder with Anthropic provider
        anthropic_builder = WorkflowBuilder(
            endpoints=self.endpoints, openapi_spec=self.openapi_spec
        )

        # Create a workflow from the identified workflow
        with patch.object(anthropic_builder, "_create_steps") as mock_create_steps:
            # Mock the _create_steps method to add steps to the steps list
            def side_effect(workflow, temp_workflow):
                temp_workflow["steps"].append(
                    {
                        "stepId": "list-pets",
                        "description": "List all pets",
                        "operation": {
                            "operationId": "listPets",
                            "path": "/pets",
                            "method": "get",
                        },
                        "outputs": {
                            "pets_list": "$response.body",
                            "count": "$response.body.length",
                        },
                    }
                )
                temp_workflow["steps"].append(
                    {
                        "stepId": "get-pet",
                        "description": "Get a specific pet",
                        "operation": {
                            "operationId": "getPetById",
                            "path": "/pets/{petId}",
                            "method": "get",
                        },
                        "parameters": [
                            {
                                "name": "petId",
                                "value": "$steps.list-pets.outputs.pets_list[0].id",
                            }
                        ],
                        "outputs": {"pet_details": "$response.body"},
                    }
                )

            mock_create_steps.side_effect = side_effect

            workflow = anthropic_builder.create_workflow(self.identified_workflow)

            # Verify the workflow properties
            self.assertEqual(
                workflow["workflowId"], to_kebab_case(self.identified_workflow["name"])
            )

        # Create a WorkflowBuilder with OpenAI provider
        openai_builder = WorkflowBuilder(endpoints=self.endpoints, openapi_spec=self.openapi_spec)

        # Create a workflow from the identified workflow
        with patch.object(openai_builder, "_create_steps") as mock_create_steps:
            # Mock the _create_steps method to add steps to the steps list
            def side_effect(workflow, temp_workflow):
                temp_workflow["steps"].append(
                    {
                        "stepId": "list-pets",
                        "description": "List all pets",
                        "operation": {
                            "operationId": "listPets",
                            "path": "/pets",
                            "method": "get",
                        },
                        "outputs": {
                            "pets_list": "$response.body",
                            "count": "$response.body.length",
                        },
                    }
                )
                temp_workflow["steps"].append(
                    {
                        "stepId": "get-pet",
                        "description": "Get a specific pet",
                        "operation": {
                            "operationId": "getPetById",
                            "path": "/pets/{petId}",
                            "method": "get",
                        },
                        "parameters": [
                            {
                                "name": "petId",
                                "value": "$steps.list-pets.outputs.pets_list[0].id",
                            }
                        ],
                        "outputs": {"pet_details": "$response.body"},
                    }
                )

            mock_create_steps.side_effect = side_effect

            workflow = openai_builder.create_workflow(self.identified_workflow)

            # Verify the workflow properties
            self.assertEqual(
                workflow["workflowId"], to_kebab_case(self.identified_workflow["name"])
            )


if __name__ == "__main__":
    unittest.main()
