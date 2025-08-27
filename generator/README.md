# Jentic Arazzo Generator [Beta]

[![Discord](https://img.shields.io/badge/JOIN%20OUR%20DISCORD-COMMUNITY-7289DA?style=plastic&logo=discord&logoColor=white)](https://discord.gg/yrxmDZWMqB)
[![Contributor Covenant](https://img.shields.io/badge/Contributor%20Covenant-3.0-40c463.svg)](https://github.com/jentic/arazzo-engine/blob/HEAD/CODE_OF_CONDUCT.md)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://github.com/jentic/arazzo-engine/blob/HEAD/LICENSE)

A tool for analyzing OpenAPI specifications and generating meaningful Arazzo workflows by identifying logical API sequences and patterns.

## Overview

The Jentic Arazzo Generator transforms OpenAPI specifications into Arazzo workflows, facilitating the creation of well-structured, user-centric API sequences. It employs LLM-powered intelligence to identify workflows that represent real-world use cases and valuable user journeys.

Arazzo is a workflow specification that describes sequences of API calls and their dependencies to achieve specific outcomes. The generated workflows improve API documentation by showing developers not just individual endpoints, but meaningful sequences that accomplish complete business tasks.

> **Join our community!** Connect with contributors and users on [Discord](https://discord.gg/yrxmDZWMqB) to discuss ideas, ask questions, and collaborate on the Jentic Arazzo Generator repository.

## Key Features

- **OpenAPI Parser**: Robust parsing of OpenAPI v3.0 and v3.1 specifications with extensive error handling
- **LLM-Powered Workflow Analysis**:
  - Intelligent identification of workflows
  - Context-aware discovery of meaningful API sequences
  - Natural language descriptions of workflow purposes
- **Arazzo Generator**: Creates compliant Arazzo specifications from identified workflows
- **Arazzo Validator**: Ensures generated specifications adhere to the Arazzo schema

## Installation

1. Install PDM if you haven't already:
   ```bash
   # Install PDM
   curl -sSL https://pdm.fming.dev/install-pdm.py | python3 -
   
   # Or with Homebrew (macOS/Linux)
   brew install pdm
   
   # Or with pip
   pip install pdm
   ```

2. Install project dependencies:
   ```bash
   # Install dependencies
   pdm install
   ```

## Configuration

### Method 1: Using Environment File (Recommended)

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit the `.env` file with your preferred text editor and add your API keys:
   ```bash
   # Example .env file
   GEMINI_API_KEY=your_gemini_key_here
   ANTHROPIC_API_KEY=your_anthropic_key_here
   OPENAI_API_KEY=your_openai_key_here
   ```

### Method 2: Using Shell Environment Variables

You can set the API keys directly in your shell session:

```bash
# For current session only
export GEMINI_API_KEY=your_gemini_key_here
export ANTHROPIC_API_KEY=your_anthropic_key_here
export OPENAI_API_KEY=your_openai_key_here
```

## Usage

### Basic Usage

To generate an Arazzo workflow specification from an OpenAPI file using LLM-based analysis:

```bash
pdm run generate <openapi_file_path> -o <output_file_path>
```

Example:
```bash
pdm run generate /path/to/openapi.yaml -o ./output.yaml
```

You can also generate output in JSON format:
```bash
pdm run generate /path/to/openapi.yaml -o ./output.json --format json
```

Or use the shorter option flag:
```bash
pdm run generate /path/to/openapi.yaml -o ./output.json -f json
```

### Validation

To validate an existing Arazzo specification in either YAML or JSON format:

```bash
pdm run validate /path/to/arazzo.yaml
# OR
pdm run validate /path/to/arazzo.json
```

The validator automatically detects the format based on the file extension.

## Architecture

### Core Components

#### 1. OpenAPI Parser (`openapi_parser.py`)
- Fetches and parses OpenAPI specifications from URLs or local files (OpenAPI v3.0 and v3.1)
- Utilises prance for parsing and validation (https://pypi.org/project/prance/)
- Provides robust error handling for imperfect real-world specifications
- Extracts endpoints, schemas, and metadata for further analysis

#### 2. Workflow Analyzer (`llm_analyzer.py`)
- **LLM Integration**:
  - Workflow identification with contextual understanding and LLM-powered analysis
  - Workflow validation and filtering

#### 3. LLM Service (`llm/litellm_service.py`)
- Connects to LLMs for intelligent analysis
- Supports multiple LLM providers (e.g., OpenAI, Anthropic, Gemini) using LiteLLM
- Uses carefully crafted prompts for endpoint analysis and workflow validation
- Processes and cleans API responses for reliable integration

#### 4. Arazzo Generator (`arazzo_generator.py`)
- Transforms identified workflows into valid Arazzo specifications
- Creates structured step sequences with appropriate parameters and outputs
- Handles formatting and encoding for compliance with Arazzo schema

#### 5. Arazzo Validator (`arazzo_validator.py`)
- Validates generated specifications against the Arazzo schema
- Provides detailed error messages for troubleshooting
- Supports validation from local files, URLs, or embedded schema

#### 6. Command-Line Interface (`cli/main.py`)
- Provides a user-friendly interface for generation and validation
- Supports customization of LLM settings and output formats
- Includes comprehensive logging for visibility into the process

## Docker

The project includes Docker configurations for both the API server and CLI tool modes, making it easy to deploy to environments like AWS ECS.

### Quick Start with Docker

```bash
# Build the Docker image
docker build -t jentic-arazzo-generator -f docker/Dockerfile .

# Run the API server
docker run -p 8000:8000 \
  -e ANTHROPIC_API_KEY=your_api_key \
  -e OPENAI_API_KEY=your_api_key \
  -e GEMINI_API_KEY=your_api_key \
  jentic-arazzo-generator

# Run the CLI tool
docker run --rm \
  -e ANTHROPIC_API_KEY=your_api_key \
  -e OPENAI_API_KEY=your_api_key \
  -e GEMINI_API_KEY=your_api_key \
  -v $(pwd)/output:/app/output \
  jentic-arazzo-generator pdm run generate <url> --output /app/output/result.yaml
```

For detailed Docker instructions including AWS ECS deployment, see the [Docker README](docker/README.md).

### Running the API Server locally

```bash
# Run the API server
pdm run uvicorn arazzo_generator.api.app:app --host 0.0.0.0 --port 8000
```

```bash
curl -s -X POST "http://localhost:8000/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://raw.githubusercontent.com/jentic/jentic-public-apis/refs/heads/main/apis/openapi/yelp.com/main/1.0.0/openapi.json",
    "format": "json",
    "validate_spec": true,
    "enable_llm": true,
    "llm_provider": "gemini" 
  }' | jq -r '.arazzo_spec' | jq '.' > arazzo_spec.json
```


## Development

### Running Tests

```bash
# Run all tests
pdm run test

# Run a specific test file
pdm run test tests/test_parser.py
```

### Code Formatting

```bash
# Check formatting without making changes
pdm run check-format

# Format code with black and isort
pdm run format

```

### Available PDM Scripts

- `pdm run generate` - Generate Arazzo workflows from OpenAPI specs
- `pdm run validate` - Validate Arazzo workflow files
- `pdm run batch` - Batch process multiple OpenAPI specs to generate Arazzo workflows
- `pdm run test` - Run all tests
- `pdm run format` - Format code with black and isort
- `pdm run check-format` - Check code formatting without making changes
- `pdm run lint` - Run static type checking and linting


### LLM Configuration

You can configure the LLM provider and model in the `config.toml` file:

```toml
[llm]
# Example supported providers: "gemini", "openai", "anthropic"
llm_provider = "gemini"

# Recommended model to use due to Gemini's large context window
llm_model = "gemini/gemini-2.0-flash"
```

### Logging Configuration

The application uses a centralized logging system configured via the `config.toml` file in the project root. This system handles both application logs and LLM interaction logs (prompts and responses).

#### Configurable Options

You can customize the following logging settings in `config.toml`:

```toml
[logging]
# Log format using standard Python logging format strings
format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Output destinations: "console", "file", or both
destinations = ["console", "file"]

# Default log level: DEBUG, INFO, WARNING, ERROR, CRITICAL
level = "INFO"

# File logging configuration
[logging.file]
log_dir = "logs"  # Directory for log files
filename = "jentic.log"  # Application log filename
```

#### Log Directory Structure

Logs are stored in timestamped directories under the `logs` folder:

```
logs/
└── 20250725_104937/  # Timestamped directory for each run
    ├── jentic.log  # Application logs
    ├── workflow_analysis_prompt.txt  # LLM prompts
    └── workflow_analysis_response.txt  # LLM responses
```

This unified structure ensures all logs from a single execution (both application logs and LLM interactions) are stored together in the same directory.

### Project Structure
See [STRUCTURE.md](STRUCTURE.md) for a detailed description of the project structure.

### Integration with jentic-public-apis
This Arazzo Generator powers the automated workflow generation in the [jentic-public-apis](https://github.com/jentic/jentic-public-apis) repository. To generate an Arazzo specification from an OpenAPI spec:

1. Create a new 'Generate Arazzo Specification...' issue in the [jentic-public-apis](https://github.com/jentic/jentic-public-apis) repository
2. Include the URL to your OpenAPI specification (must be publicly accessible)
3. Optionally, specify any specific workflows you'd like to generate

The system will automatically process your request and generate the corresponding Arazzo specification. You'll be notified when the generation is complete.

