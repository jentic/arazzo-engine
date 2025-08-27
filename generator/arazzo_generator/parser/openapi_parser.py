"""OpenAPI specification parser module."""

import json
import os
import re
from typing import Any

import prance
import requests
import yaml
from openapi_spec_validator import validate
from prance.util.fs import abspath
from prance.util.url import absurl

from arazzo_generator.utils.logging import get_logger

logger = get_logger(__name__)


class OpenAPIParser:
    """OpenAPI specification parser.

    This class is responsible for fetching and parsing OpenAPI specifications from URI-Reference.
    It supports OpenAPI versions 3.0.x/3.1.x, with robust error handling for real-world
    specifications that may not strictly follow standards.

    Local or remote references are not resolved during the parsing.
    This avoids possible security issues with local file access.
    """

    def __init__(self, url: str):
        """Initialize the OpenAPI parser with a URI-Reference to an OpenAPI specification.

        Parameters:
        url (string): The URI-Reference to the OpenAPI specification.
        """
        self.url_parsed = absurl(url, abspath(os.getcwd()))
        self.url = self.url_parsed.geturl()
        self.spec = None
        self.paths = {}
        self.components = {}
        self.version = None
        self.parser = None

    def fetch_spec(self) -> dict[str, Any]:
        """Fetch the OpenAPI specification from the URL.

        Returns:
            The OpenAPI specification as a dictionary.

        Raises:
            ValueError: If the response is not valid JSON or YAML.
            requests.RequestException: If the request to the URL fails.
            FileNotFoundError: If the local file is not found.
        """
        logger.info(f"Reading OpenAPI spec from '{self.url}'")

        try:
            # First, try to use prance to parse the spec
            try:
                logger.debug(
                    "Attempting to parse OpenAPI spec with prance", extra={"url": self.url}
                )
                parser = prance.BaseParser(self.url, strict=False)
                self.spec = parser.specification
                self.parser = parser
                logger.info("Successfully parsed spec with prance", extra={"url": self.url})
            except Exception as e:
                logger.warning(f"Prance parsing failed: {e}", extra={"url": self.url})
                # Fall back to manual fetching and parsing with robust error handling
                self.spec = self._fetch_and_parse_with_fallbacks()

            if not self.spec:
                raise ValueError("Empty OpenAPI spec")

            # Extract metadata regardless of how we parsed it
            # This is where the paths and components are extracted and added to self
            self._extract_metadata()
            return self.spec

        except requests.RequestException as e:
            logger.exception(f"Failed to fetch OpenAPI spec: {e}", extra={"url": self.url})
            raise

    def _fetch_and_parse_with_fallbacks(self) -> dict[str, Any]:
        """Fetch and parse the OpenAPI spec with fallback mechanisms.

        Returns:
            The parsed OpenAPI specification as a dictionary.

        Raises:
            ValueError: If all parsing methods fail.
        """

        try:
            # Get the content depending on whether it's a file or URL
            if self.url_parsed.schema == "file":
                logger.debug(f"Reading local file '{self.url}'")
                try:
                    with open(self.url, "rb") as f:
                        raw_content = f.read()
                except Exception as e:
                    logger.exception(f"Failed to read local file: {e}", extra={"url": self.url})
                    raise ValueError(f"Failed to read OpenAPI specification file: {e}") from e
            else:
                # It's a URL
                logger.debug(f"Fetching from URL: {self.url}")
                response = requests.get(self.url, timeout=100)
                response.raise_for_status()
                raw_content = response.content

            # First, try to decode as UTF-8
            try:
                content = raw_content.decode("utf-8")
            except UnicodeDecodeError:
                # If UTF-8 decoding fails, try with ISO-8859-1 (Latin-1) which accepts all byte values
                logger.warning(
                    "UTF-8 decoding failed, trying with ISO-8859-1", extra={"url": self.url}
                )
                content = raw_content.decode("iso-8859-1")

            # Clean the content
            content = self._clean_spec_content(content)

            # Try to parse as JSON
            try:
                spec = json.loads(content)
                logger.debug("Successfully parsed spec as JSON", extra={"url": self.url})
            except json.JSONDecodeError:
                # Try as YAML
                try:
                    spec = yaml.safe_load(content)
                    logger.debug("Successfully parsed spec as YAML", extra={"url": self.url})
                except yaml.YAMLError as e1:
                    # Try to fix common YAML structural issues
                    logger.warning(f"YAML parsing failed: {e1}", extra={"url": self.url})
                    fixed_content = self._fix_yaml_structure(content)
                    try:
                        spec = yaml.safe_load(fixed_content)
                        logger.info(
                            "Successfully parsed spec after fixing YAML structure",
                            extra={"url": self.url},
                        )
                    except yaml.YAMLError:
                        # Last resort: try alternative parsing methods
                        logger.warning(
                            "Failed to parse after fixing structure {e2}",
                            extra={"url": self.url},
                        )
                        spec = self._try_alternative_parsing_methods(raw_content)

            # Validate the spec
            try:
                validate(spec)
                logger.info("OpenAPI spec validation successful", extra={"url": self.url})
            except Exception as e:
                logger.warning(f"OpenAPI spec validation failed: {e}")
                # Continue despite validation errors

            return spec

        except requests.RequestException as e:
            logger.error(f"Failed to fetch from URL {self.url}")
            raise ValueError(f"Failed to fetch OpenAPI specification: {e}") from e
        except Exception as e:
            logger.error(f"All parsing methods failed: {e}", extra={"url": self.url})
            raise ValueError("Failed to parse OpenAPI specification") from e

    def _clean_spec_content(self, content: str) -> str:
        """Clean the OpenAPI spec content to handle common issues.

        Args:
            content: The raw content of the OpenAPI spec.

        Returns:
            The cleaned content.
        """
        # Replace common problematic characters
        cleaned = content

        # Replace UTF-8 BOM if present
        if cleaned.startswith("\ufeff"):
            cleaned = cleaned[1:]

        # Replace non-breaking spaces with regular spaces
        cleaned = cleaned.replace("\u00a0", " ")

        # Replace various dash characters with standard dash
        cleaned = cleaned.replace("\u2013", "-")  # en dash
        cleaned = cleaned.replace("\u2014", "-")  # em dash

        # Replace smart quotes with straight quotes
        cleaned = cleaned.replace("\u201c", '"')  # left double quote
        cleaned = cleaned.replace("\u201d", '"')  # right double quote
        cleaned = cleaned.replace("\u2018", "'")  # left single quote
        cleaned = cleaned.replace("\u2019", "'")  # right single quote

        # Handle Windows line endings
        cleaned = cleaned.replace("\r\n", "\n")

        return cleaned

    def _fix_yaml_structure(self, content: str) -> str:
        """Fix common structural issues in YAML content.

        Args:
            content: The YAML content to fix.

        Returns:
            The fixed YAML content.
        """
        # Fix common structural issues in YAML
        fixed = content

        # Fix missing spaces after colons in mappings
        fixed = re.sub(r"([a-zA-Z0-9_-]+):([$a-zA-Z0-9])", r"\1: \2", fixed)

        # Fix missing line breaks between mappings
        fixed = re.sub(r"([a-zA-Z0-9_-]+): ([^{\[\n].*?)([a-zA-Z0-9_-]+):", r"\1: \2\n\3:", fixed)

        # Fix indentation of nested mappings
        lines = fixed.split("\n")
        fixed_lines = []
        for i, line in enumerate(lines):
            fixed_lines.append(line)
            if (
                ":" in line
                and i + 1 < len(lines)
                and not lines[i + 1].startswith(" ")
                and not lines[i + 1].startswith("-")
                and ":" in lines[i + 1]
            ):
                indent = " " * 2  # Default indentation of 2 spaces
                fixed_lines[-1] = line + "\n" + indent

        fixed = "\n".join(fixed_lines)

        logger.info("Fixed YAML structure issues", extra={"url": self.url})
        return fixed

    def _try_alternative_parsing_methods(self, content: bytes) -> dict[str, Any]:
        """Try alternative methods to parse the OpenAPI spec.

        Args:
            content: The raw binary content of the OpenAPI spec.

        Returns:
            The parsed OpenAPI spec.

        Raises:
            ValueError: If all parsing methods fail.
        """
        logger.info("Attempting alternative parsing methods", extra={"url": self.url})

        # Method 1: Try to parse after cleaning the content
        try:
            # Decode with lenient encoding
            text_content = content.decode("utf-8", errors="replace")
            cleaned_content = self._clean_spec_content(text_content)
            spec = yaml.safe_load(cleaned_content)
            logger.info("Successfully parsed spec with safe YAML loader", extra={"url": self.url})
            return spec
        except Exception as e:
            logger.warning(f"Alternative method 1 failed: {e}", extra={"url": self.url})

        # Method 2: Try to convert YAML to JSON using a regexp-based approach
        try:
            text_content = content.decode("utf-8", errors="replace")
            cleaned_content = self._clean_spec_content(text_content)
            # Very simplistic YAML to JSON conversion (only handles basic structures)
            # Replace YAML indentation with JSON nesting
            json_like = cleaned_content
            # 1) "key": "value",
            json_like = re.sub(
                r"^(?P<i>[^\S\n]*)(?P<k>[\w-]+):[^\S\n]*(?P<v>[^\n][^\n]*?)(?=[^\S\n]*$)",
                r'\g<i>"\g<k>": "\g<v>",',
                json_like,
                flags=re.MULTILINE,
            )

            # key: -> "key": {
            json_like = re.sub(
                r"^(?P<i>[^\S\n]*)(?P<k>[\w-]+):[^\S\n]*$",
                r'\g<i>"\g<k>": {',
                json_like,
                flags=re.MULTILINE,
            )
            json_like = "{" + json_like + "}"
            # Attempt to parse the JSON-like content
            spec = json.loads(json_like)
            logger.info(
                "Successfully parsed spec with YAML-to-JSON conversion", extra={"url": self.url}
            )
            return spec
        except Exception as e:
            logger.warning(f"Alternative method 2 failed: {e}", extra={"url": self.url})

        # Method 3: Try using a custom tokenizer approach (simplified)
        try:
            text_content = content.decode("utf-8", errors="replace")
            # Create a simple dictionary with basic OpenAPI structure
            spec = {
                "openapi": "3.0.0",
                "info": {"title": "Extracted API", "version": "1.0.0"},
                "paths": {},
            }

            # Extract path information using regular expressions
            path_pattern = re.compile(r"^\s*/([^:]+):", re.MULTILINE)
            paths = path_pattern.findall(text_content)

            # Create basic path entries
            for path in paths:
                spec["paths"]["/" + path] = {"get": {"responses": {"200": {"description": "OK"}}}}

            logger.info(
                f"Generated basic spec structure with {len(paths)} paths using fallback method",
                extra={"url": self.url},
            )
            return spec
        except Exception as e:
            logger.warning(f"Alternative method 3 failed: {e}", extra={"url": self.url})

        # If all methods fail, raise an exception
        raise ValueError("All parsing methods failed")

    def _extract_metadata(self) -> None:
        """Extract metadata from the OpenAPI specification."""
        if not self.spec:
            return

        # Get version
        if "openapi" in self.spec:
            self.version = self.spec["openapi"]
        elif "swagger" in self.spec:
            self.version = self.spec["swagger"]

        # Get paths
        self.paths = self.spec.get("paths", {})

        # Get components
        self.components = self.spec.get("components", {})

    def get_endpoints(self) -> dict[str, dict[str, Any]]:
        """Extract all endpoints from the OpenAPI specification.

        Returns:
            A dictionary of all endpoints with their methods, parameters, and schemas.
        """
        if not self.spec:
            self.fetch_spec()

        endpoints = {}

        for path, path_item in self.paths.items():
            endpoint_data = {}

            # Extract path parameters
            path_parameters = path_item.get("parameters", [])

            # Process HTTP methods
            for method in ["get", "post", "put", "patch", "delete", "options", "head"]:
                if method in path_item:
                    operation = path_item[method]

                    # Combine path parameters with operation parameters
                    parameters = path_parameters.copy()
                    parameters.extend(operation.get("parameters", []))

                    # Extract request body and preserve references
                    request_body = operation.get("requestBody", {})

                    # Extract responses and preserve references
                    responses = operation.get("responses", {})

                    endpoint_data[method] = {
                        "operation_id": operation.get("operationId"),
                        "summary": operation.get("summary"),
                        "description": operation.get("description"),
                        "parameters": parameters,
                        "request_body": request_body,
                        "responses": responses,
                        "security": operation.get("security", []),
                        "tags": operation.get("tags", []),
                    }

            if endpoint_data:
                endpoints[path] = endpoint_data

        return endpoints

    def get_schemas(self) -> dict[str, Any]:
        """Extract all schemas from the OpenAPI specification.

        Returns:
            A dictionary of all schemas in the components section.
        """
        if not self.spec:
            self.fetch_spec()

        return self.components.get("schemas", {})

    def get_parameters(self) -> dict[str, Any]:
        """Extract all parameters from the OpenAPI specification.

        Returns:
            A dictionary of all parameters in the components section.
        """
        if not self.spec:
            self.fetch_spec()

        return self.components.get("parameters", {})

    def get_responses(self) -> dict[str, Any]:
        """Extract all responses from the OpenAPI specification.

        Returns:
            A dictionary of all responses in the components section.
        """
        if not self.spec:
            self.fetch_spec()

        return self.components.get("responses", {})

    def get_request_bodies(self) -> dict[str, Any]:
        """Extract all request bodies from the OpenAPI specification.

        Returns:
            A dictionary of all request bodies in the components section.
        """
        if not self.spec:
            self.fetch_spec()

        return self.components.get("requestBodies", {})

    def get_security_schemes(self) -> dict[str, Any]:
        """Extract all security schemes from the OpenAPI specification.

        Returns:
            A dictionary of all security schemes in the components section.
        """
        if not self.spec:
            self.fetch_spec()

        return self.components.get("securitySchemes", {})

    def resolve_reference(self, ref: str) -> dict[str, Any]:
        """Resolve a reference to its actual content.

        Args:
            ref: A reference string (e.g., '#/components/schemas/Pet')

        Returns:
            The resolved content of the reference.

        Raises:
            ValueError: If the reference cannot be resolved.
        """
        if not ref.startswith("#"):
            # External reference - use prance resolver if available
            if self.parser and isinstance(self.parser, prance.ResolvingParser):
                try:
                    resolver = self.parser.resolver
                    return resolver.resolve_reference(ref)[0]
                except Exception:
                    logger.warning(f"Failed to resolve external reference {ref}", exc_info=True)

        # Local reference or fallback for external
        try:
            parts = ref.split("/")
            if parts[0] == "#":
                parts = parts[1:]  # Remove the # prefix

            # Navigate through the spec to find the referenced object
            current = self.spec
            for part in parts:
                if part in current:
                    current = current[part]
                else:
                    raise ValueError(f"Reference part '{part}' not found in the specification")

            return current
        except Exception as e:
            logger.error(f"Failed to resolve reference {ref}: {e}")
            raise ValueError(f"Could not resolve reference {ref}: {e}") from e
