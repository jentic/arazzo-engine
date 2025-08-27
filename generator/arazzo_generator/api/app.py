"""FastAPI application for Arazzo generator.

This module provides a REST API for generating Arazzo specifications from OpenAPI URLs.
"""

import re
from typing import Any, Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

from arazzo_generator.generator.generator_service import generate_arazzo
from arazzo_generator.utils.config import get_config
from arazzo_generator.utils.exceptions import InvalidUserWorkflowError, SpecValidationError
from arazzo_generator.utils.logging import get_logger

logger = get_logger(__name__)
config = get_config()

# Create FastAPI app
app = FastAPI(
    title="Arazzo Generator API",
    description="API for generating Arazzo specifications from OpenAPI specifications",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)


# Request models
class GenerateRequest(BaseModel):
    """Request model for generating Arazzo specifications."""

    url: str = Field(
        ...,
        description="URL to the OpenAPI specification (http, https, or file URLs are supported)",
    )
    format: Literal["json", "yaml"] = Field(
        "json", description="Output format for the generated Arazzo spec"
    )
    validate_spec: bool = Field(True, description="Validate the generated Arazzo spec")
    direct_llm: bool = Field(
        False, description="Enable direct LLM generation of Arazzo specification"
    )
    api_key: str | None = Field(None, description="API key for LLM service")
    llm_model: str | None = Field(
        default=config.llm.llm_model,
        description="LLM model to use for analysis. If not provided, the default config model will be used.",
    )
    llm_provider: str | None = Field(
        default=config.llm.llm_provider,
        description="LLM provider to use. If not provided, the default config provider will be used.",
    )
    workflow_descriptions: list[str] | None = Field(
        None,
        description=(
            "Optional list of workflow descriptions (as strings) to guide the generator in creating specific workflows requested by the user. "
            "If provided, the generator will attempt to create only these workflows using the OpenAPI spec."
        ),
    )

    @field_validator("url")
    @classmethod
    def validate_url(cls, v):
        """Validate that the URL is a valid http, https, or file URL."""
        if not re.match(r"^(http|https|file)://", v):
            raise ValueError("URL scheme must be http, https, or file")
        return v


class GenerationResponse(BaseModel):
    """Response model for generation results."""

    is_valid: bool = Field(..., description="Whether the generated Arazzo spec is valid")
    validation_errors: list[str] = Field([], description="List of validation errors if not valid")
    arazzo_spec: dict[str, Any] = Field(..., description="The generated Arazzo specification")
    content: str = Field(..., description="The serialized Arazzo specification (JSON or YAML)")
    fallback_used: bool = Field(
        False,
        description="Whether fallback logic (retry without workflow_descriptions) was used",
    )
    message: str | None = Field(
        None, description="Optional informational message about the generation process"
    )


@app.get("/")
async def root():
    """Root endpoint returning API information."""
    return {
        "name": "Arazzo Generator API",
        "version": "1.0.0",
        "description": "API for generating Arazzo specifications from OpenAPI URLs",
    }


@app.post("/generate", response_model=GenerationResponse)
async def generate_endpoint(request: GenerateRequest):
    """Generate an Arazzo specification from an OpenAPI specification URL."""
    try:
        # Call the service function
        arazzo_spec, arazzo_content, is_valid, validation_errors, fallback_used = generate_arazzo(
            url=str(request.url),
            format=request.format,
            validate_spec=request.validate_spec,
            direct_llm=request.direct_llm,
            api_key=request.api_key,
            llm_model=request.llm_model,
            llm_provider=request.llm_provider,
            workflow_descriptions=request.workflow_descriptions,
        )

        if not arazzo_spec:
            # Specific error when user provided custom workflow descriptions resulting in no valid arazzo spec
            if request.workflow_descriptions:
                raise HTTPException(
                    status_code=400,
                    detail="Unable to generate a valid Arazzo specification with the provided workflow_descriptions.",
                )
            # Generic failure otherwise
            raise HTTPException(
                status_code=500, detail="Failed to generate valid Arazzo specification"
            )

        return GenerationResponse(
            is_valid=is_valid,
            validation_errors=validation_errors,
            arazzo_spec=arazzo_spec,
            content=arazzo_content,
            fallback_used=fallback_used,
            message=(
                (
                    "Initial generation using provided workflow descriptions failed. Generator retried without those descriptions and succeeded."
                )
                if fallback_used
                else None
            ),
        )

    except InvalidUserWorkflowError as e:
        logger.warning(f"Invalid user workflow requested: {e.requested_workflows}")
        raise HTTPException(status_code=422, detail=str(e)) from None

    except SpecValidationError as e:
        logger.error(f"Spec validation error: {e.errors}")
        raise HTTPException(
            status_code=400, detail={"message": str(e), "errors": e.errors}
        ) from None

    except Exception as e:
        logger.error(f"Error generating Arazzo specification: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error generating Arazzo specification: {e}"
        ) from None
