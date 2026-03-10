# Docling Serve API Usage with Arazzo

This guide explains how to use the Docling Serve API locally with [Arazzo](https://github.com/arazzo/arazzo) for executing OpenAPI operations.

## Prerequisites

- Python 3.10+ with `uv` package manager
- Docling Serve repository cloned and dependencies installed
- Arazzo installed in your target repository

## Starting the API Server

### 1. Install Dependencies

```bash
cd docling-serve
uv sync
```

### 2. Start the Server

Run the API server in development mode:

```bash
uv run docling-serve dev --host 127.0.0.1 --port 5001 --no-enable-ui
```

The server will be available at:
- **API Base URL**: `http://127.0.0.1:5001`
- **OpenAPI Spec**: `http://127.0.0.1:5001/openapi.json`
- **OpenAPI 3.0.3 Spec**: `http://127.0.0.1:5001/openapi-3.0.json`
- **API Documentation**: `http://127.0.0.1:5001/docs`

### 3. Verify Server is Running

```bash
curl http://127.0.0.1:5001/health
```

Expected response:
```json
{"status": "ok"}
```

## OpenAPI Specification

The API provides OpenAPI specifications in two versions:

1. **OpenAPI 3.1.0** (default): `http://127.0.0.1:5001/openapi.json`
2. **OpenAPI 3.0.3** (compatible): `http://127.0.0.1:5001/openapi-3.0.json`

For Arazzo, you can use either version. The 3.0.3 version is recommended for maximum compatibility.

### Exporting the OpenAPI Spec

To save the OpenAPI spec locally:

```bash
# OpenAPI 3.1.0
curl http://127.0.0.1:5001/openapi.json > openapi.json

# OpenAPI 3.0.3 (recommended for Arazzo)
curl http://127.0.0.1:5001/openapi-3.0.json > openapi-3.0.json
```

Or use the provided export script:

```bash
uv run python export_openapi.py
```

This creates:
- `openapi.json` (OpenAPI 3.1.0)
- `openapi-3.0.json` (OpenAPI 3.0.3)

## Using with Arazzo

### Arazzo Configuration

In your Arazzo configuration file, reference the OpenAPI spec:

```yaml
# arazzo-config.yaml
openapi:
  spec: http://127.0.0.1:5001/openapi-3.0.json
  # Or use a local file:
  # spec: ./openapi-3.0.json
  
server:
  base_url: http://127.0.0.1:5001
```

### Authentication

By default, the API runs **without authentication**. If you need to enable API key authentication:

1. Set the environment variable:
   ```bash
   export DOCLING_SERVE_API_KEY="your-secret-key"
   ```

2. Restart the server

3. In Arazzo, configure the API key:
   ```yaml
   security:
     - ApiKeyAuth:
         api_key: "your-secret-key"
   ```

   Or in the request headers:
   ```yaml
   headers:
     X-Api-Key: "your-secret-key"
   ```

## Key API Endpoints

### 1. Health Check

**Endpoint**: `GET /health`

**Arazzo Example**:
```yaml
operations:
  - name: health_check
    method: GET
    path: /health
```

### 2. Convert Document from URL (Synchronous)

**Endpoint**: `POST /v1/convert/source`

**Request Body**:
```json
{
  "sources": [
    {
      "kind": "http",
      "url": "https://arxiv.org/pdf/2206.01062"
    }
  ],
  "options": {
    "to_formats": ["md", "json"],
    "ocr": false,
    "pdf_backend": "dlparse_v2",
    "table_mode": "fast"
  },
  "target": {
    "kind": "inbody"
  }
}
```

**Arazzo Example**:
```yaml
operations:
  - name: convert_url_sync
    method: POST
    path: /v1/convert/source
    requestBody:
      content:
        application/json:
          schema:
            type: object
            properties:
              sources:
                type: array
                items:
                  type: object
                  properties:
                    kind:
                      type: string
                      enum: [http]
                    url:
                      type: string
              options:
                type: object
                properties:
                  to_formats:
                    type: array
                    items:
                      type: string
                      enum: [md, json, html, text, doctags]
                  ocr:
                    type: boolean
                    default: false
    body:
      sources:
        - kind: http
          url: "https://arxiv.org/pdf/2206.01062"
      options:
        to_formats: [md, json]
        ocr: false
```

**Response**:
```json
{
  "document": {
    "md_content": "...",
    "json_content": {...},
    "html_content": "...",
    "text_content": "..."
  },
  "status": "success",
  "processing_time": 28.15,
  "errors": []
}
```

**Note**: Synchronous endpoints have a 2-minute timeout. For longer conversions, use async endpoints.

### 3. Convert Document from URL (Async)

**Endpoint**: `POST /v1/convert/source/async`

**Request Body**: Same as synchronous endpoint

**Response**:
```json
{
  "task_id": "abc123-def456-...",
  "task_type": "convert",
  "task_status": "queued",
  "task_position": 0
}
```

**Arazzo Example**:
```yaml
operations:
  - name: convert_url_async
    method: POST
    path: /v1/convert/source/async
    body:
      sources:
        - kind: http
          url: "https://arxiv.org/pdf/2206.01062"
      options:
        to_formats: [md]
        ocr: false
```

### 4. Get Task Status

**Endpoint**: `GET /v1/status/poll/{task_id}`

**Arazzo Example**:
```yaml
operations:
  - name: get_task_status
    method: GET
    path: /v1/status/poll/{task_id}
    parameters:
      - name: task_id
        in: path
        required: true
        schema:
          type: string
      - name: wait
        in: query
        schema:
          type: number
          default: 0.0
```

### 5. Get Task Result

**Endpoint**: `GET /v1/result/{task_id}`

**Arazzo Example**:
```yaml
operations:
  - name: get_task_result
    method: GET
    path: /v1/result/{task_id}
    parameters:
      - name: task_id
        in: path
        required: true
        schema:
          type: string
```

### 6. Convert Document from File

**Endpoint**: `POST /v1/convert/file`

**Request**: Multipart form data

**Arazzo Example**:
```yaml
operations:
  - name: convert_file
    method: POST
    path: /v1/convert/file
    contentType: multipart/form-data
    body:
      files:
        - path/to/document.pdf
      options: |
        {
          "to_formats": ["md", "json"],
          "ocr": false
        }
      target_type: inbody
```

## Common Options

### Output Formats

- `md` - Markdown
- `json` - JSON (DoclingDocument format)
- `html` - HTML
- `text` - Plain text
- `doctags` - DocTags XML format

### OCR Configuration

```yaml
options:
  ocr: false  # Set to true if OCR is needed
  ocr_engine: "auto"  # Options: auto, easyocr, tesseract, rapidocr, tesserocr, ocrmac
  ocr_lang: ["en"]  # Language codes for OCR
```

**Note**: OCR engines are optional dependencies. Install with:
```bash
uv sync --extra easyocr
# or
uv sync --extra tesserocr
# or
uv sync --extra rapidocr
```

### PDF Backend

```yaml
options:
  pdf_backend: "dlparse_v2"  # Options: pypdfium2, dlparse_v1, dlparse_v2, dlparse_v4
```

### Table Mode

```yaml
options:
  table_mode: "fast"  # Options: fast, accurate
```

## Complete Arazzo Workflow Example

```yaml
# Complete workflow: Convert document asynchronously and retrieve result
workflows:
  convert_document_async:
    steps:
      # Step 1: Start async conversion
      - name: start_conversion
        operation: convert_url_async
        body:
          sources:
            - kind: http
              url: "https://arxiv.org/pdf/2206.01062"
          options:
            to_formats: [md, json]
            ocr: false
        extract:
          task_id: $.task_id
      
      # Step 2: Poll for completion
      - name: wait_for_completion
        operation: get_task_status
        parameters:
          task_id: "{{ steps.start_conversion.task_id }}"
        retry:
          max_attempts: 60
          delay: 2s
        condition: $.task_status == "completed"
      
      # Step 3: Get result
      - name: get_result
        operation: get_task_result
        parameters:
          task_id: "{{ steps.start_conversion.task_id }}"
        extract:
          md_content: $.document.md_content
          json_content: $.document.json_content
```

## Environment Variables

Configure the server using environment variables:

```bash
# Server configuration
export UVICORN_HOST=127.0.0.1
export UVICORN_PORT=5001

# API configuration
export DOCLING_SERVE_ENABLE_UI=false
export DOCLING_SERVE_API_KEY=""  # Empty = no auth
export DOCLING_SERVE_MAX_SYNC_WAIT=120  # Timeout in seconds

# Engine configuration
export DOCLING_SERVE_ENG_KIND=local
export DOCLING_SERVE_ENG_LOC_NUM_WORKERS=2
```

## Troubleshooting

### Server Not Starting

1. Check if port 5001 is available:
   ```bash
   lsof -i :5001
   ```

2. Check for dependency issues:
   ```bash
   uv sync
   ```

### Timeout Errors

If you get timeout errors on synchronous endpoints:
- Use async endpoints instead
- Increase `DOCLING_SERVE_MAX_SYNC_WAIT` (default: 120 seconds)
- Use async workflow with polling

### OCR Errors

If you get OCR engine errors:
- Set `ocr: false` in options (for PDFs with text)
- Install an OCR engine: `uv sync --extra easyocr`
- Use `ocr_engine: "auto"` to auto-detect available engines

### Connection Refused

- Ensure the server is running: `curl http://127.0.0.1:5001/health`
- Check the host/port configuration
- Verify firewall settings

## Additional Resources

- **API Documentation**: http://127.0.0.1:5001/docs
- **Scalar Docs**: http://127.0.0.1:5001/scalar
- **OpenAPI Spec**: http://127.0.0.1:5001/openapi.json
- **Project Repository**: https://github.com/docling-project/docling-serve
- **Arazzo Documentation**: https://github.com/arazzo/arazzo

## Example Arazzo Test File

Save this as `test-docling-serve.yaml`:

```yaml
name: Docling Serve API Tests
base_url: http://127.0.0.1:5001

operations:
  - name: health_check
    method: GET
    path: /health
    expected_status: 200

  - name: convert_simple
    method: POST
    path: /v1/convert/source
    body:
      sources:
        - kind: http
          url: "https://arxiv.org/pdf/2206.01062"
      options:
        to_formats: [md]
        ocr: false
    expected_status: 200
    assertions:
      - path: $.status
        equals: "success"
      - path: $.document.md_content
        exists: true
```

Run with Arazzo:
```bash
arazzo run test-docling-serve.yaml
```
