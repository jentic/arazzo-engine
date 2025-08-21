# Batch Arazzo Generator

This module provides functionality for batch processing of OpenAPI specifications to generate Arazzo workflows.

## Overview

The batch module integrates with the core components of the Jentic Arazzo Generator to process multiple OpenAPI specifications in a single run. It supports:

- Processing all specifications in a repository
- Processing specifications listed in a file

## Usage

### Command-line Interface

The batch module can be used via the command-line interface:

```bash
# Process all specifications in the working repository
pdm run batch --all

# Process specifications listed in a .txt file
pdm run batch --spec-list /path/to/spec-list.txt
```

### Additional Options

```bash
# Force regeneration even if Arazzo workflow file already exists
--force

# Use a specific LLM provider
--llm-provider [gemini|anthropic|openai]

# Use a specific LLM model
--llm-model claude-3-sonnet-20240229

# Enable direct LLM generation
--direct-llm

# Set delay between processing files (in seconds)
--delay 20

# Specify directory for logs
--logs-dir logs

# Enable verbose logging
--verbose
```

### Programmatic Usage

The batch module can also be used programmatically:

```python
from arazzo_generator.batch.batch_generator import BatchProcessor

# Initialize batch processor
processor = BatchProcessor(
    llm_provider="anthropic",
    llm_model="claude-3-sonnet-20240229",
    direct_llm=False,
    logs_dir="logs"
)

# Process all specifications
success_count, total_count = processor.process_all()
```

## Logging

The batch module uses the centralized logging system configured in `config.toml`. Logs are stored in timestamped directories under the specified `log_dir`.
