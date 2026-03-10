# Execute PDF Analysis Workflow

This document provides CLI commands to execute the PDF analysis workflow using the Arazzo runner.

## Workflow Overview

The `pdf-analysis-workflow`:
1. Searches for PDFs in Google Drive (optional if `file_id` provided)
2. Downloads the PDF file
3. Converts PDF to JSON using Docling
4. Analyzes the PDF using OpenAI GPT-4o with the JSON structure
5. Returns extracted text and JSON content

## Prerequisites

### 1. Required Credentials

Set the following environment variables:

```bash
# Google Drive OAuth2 Access Token
export GOOGLEDRIVE_OAUTH2_ACCESS_TOKEN="your_google_drive_token"

# OpenAI API Key
export OPENAI_APIKEYAUTH_TOKEN="sk-your-openai-key"

# Docling API Key (if authentication is enabled)
export DOCLING_APIKEYAUTH_TOKEN="your-docling-key"
```

### 2. Check Environment Variable Mappings

To see the exact environment variable names needed:

```bash
uvx arazzo-runner show-env-mappings pdf_analysis_workflow.arazzo.json
```

## CLI Commands

### Basic Command

Execute the workflow with a search query:

```bash
uvx arazzo-runner execute-workflow \
  pdf_analysis_workflow.arazzo.json \
  --workflow-id pdf-analysis-workflow \
  --inputs '{
    "query": "mimeType='application/pdf'",
    "file_id": null,
    "analysis_prompt": "Extract and summarize all the key information from this PDF document."
  }'
```

### With Specific File ID

If you already know the Google Drive file ID:

```bash
uvx arazzo-runner execute-workflow \
  pdf_analysis_workflow.arazzo.json \
  --workflow-id pdf-analysis-workflow \
  --inputs '{
    "query": "mimeType='application/pdf'",
    "file_id": "1ABC123xyz789",
    "analysis_prompt": "Summarize the main points and extract key data from this document."
  }'
```

### Custom Analysis Prompt

```bash
uvx arazzo-runner execute-workflow \
  pdf_analysis_workflow.arazzo.json \
  --workflow-id pdf-analysis-workflow \
  --inputs '{
    "query": "name contains '\''report'\'' and mimeType='\''application/pdf'\''",
    "analysis_prompt": "Extract all tables, figures, and key statistics from this PDF. Provide a structured summary."
  }'
```

### With Server Variables

If you need to specify server URLs:

```bash
uvx arazzo-runner execute-workflow \
  pdf_analysis_workflow.arazzo.json \
  --workflow-id pdf-analysis-workflow \
  --inputs '{
    "query": "mimeType='\''application/pdf'\''",
    "file_id": null
  }' \
  --server-variables '{
    "DOCLING_SERVER": "http://127.0.0.1:5001"
  }'
```

## Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `query` | string | Yes | Google Drive search query (e.g., `"mimeType='application/pdf'"` or `"name contains 'report' and mimeType='application/pdf'"`) |
| `file_id` | string | No | Direct Google Drive file ID (skips search step if provided) |
| `analysis_prompt` | string | No | Prompt for PDF analysis (default: "Extract and summarize all the key information from this PDF document. Provide a comprehensive text summary that can be used for further reasoning.") |

## Expected Outputs

The workflow returns:

```json
{
  "extracted_text": "Summary text from OpenAI analysis...",
  "text_length": 1234,
  "ready_for_reasoning": true,
  "json_content": {
    "content": [...]
  },
  "metadata": {
    "source_file": "document.pdf",
    "source_file_id": "1ABC123xyz789",
    "analysis_method": "OpenAI GPT-4o with Docling JSON",
    "model_used": "gpt-4o",
    "docling_processing_time": 1.5
  }
}
```

## Example Workflow Execution

### Step-by-Step Example

1. **Set credentials**:
   ```bash
   export GOOGLEDRIVE_OAUTH2_ACCESS_TOKEN="ya29.a0AfH6..."
   export OPENAI_APIKEYAUTH_TOKEN="sk-proj-..."
   ```

2. **Execute workflow**:
   ```bash
   uvx arazzo-runner execute-workflow \
     pdf_analysis_workflow.arazzo.json \
     --workflow-id pdf-analysis-workflow \
     --inputs '{"query": "mimeType='\''application/pdf'\''"}'
   ```

3. **View results**: The command will output the workflow results as JSON.

## Troubleshooting

### Authentication Errors

If you get authentication errors:

1. **Google Drive**: 
   - Ensure `GOOGLEDRIVE_OAUTH2_ACCESS_TOKEN` is set
   - Token must have `https://www.googleapis.com/auth/drive` scope
   - Token may have expired (OAuth2 tokens typically expire after 1 hour)

2. **OpenAI**:
   - Verify `OPENAI_APIKEYAUTH_TOKEN` is set correctly
   - Check that the API key starts with `sk-`
   - Ensure you have sufficient credits

3. **Docling**:
   - If running locally, authentication is usually not required
   - If using a hosted instance, set `DOCLING_APIKEYAUTH_TOKEN`

### Workflow Validation Errors

Before executing, validate the workflow:

```bash
cd generator
python -m arazzo_generator.cli.main validate ../pdf_analysis_workflow.arazzo.json
```

**Note**: The workflow currently has validation errors that need to be fixed:
- Source description names need to match pattern `[A-Za-z0-9_\-]+`
- Step `inputs` should be `parameters` or `requestBody`
- Output values must be runtime expressions

### Server Connection Issues

If Docling server is not accessible:

1. **Check if server is running**:
   ```bash
   curl http://127.0.0.1:5001/health
   ```

2. **Start Docling server** (if local):
   ```bash
   cd docling-serve
   uv run docling-serve dev --host 127.0.0.1 --port 5001 --no-enable-ui
   ```

3. **Update server URL** in the workflow or use `--server-variables`

## Testing Without Credentials

To test the workflow structure without real credentials, use a mock HTTP client. See `test_workflow_mock.py` for an example.

## Logging

Enable debug logging for more details:

```bash
uvx arazzo-runner execute-workflow \
  pdf_analysis_workflow.arazzo.json \
  --workflow-id pdf-analysis-workflow \
  --inputs '{"query": "mimeType='\''application/pdf'\''"}' \
  --log-level DEBUG
```
