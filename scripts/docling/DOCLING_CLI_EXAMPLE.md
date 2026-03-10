# Docling Execute Operation Example

This document shows how to use the Arazzo runner to execute Docling operations.

## Prerequisites

1. **Start Docling Serve** (if testing with real server):
   ```bash
   cd docling-serve
   uv run docling-serve dev --host 127.0.0.1 --port 5001 --no-enable-ui
   ```

2. **Verify server is running**:
   ```bash
   curl http://127.0.0.1:5001/health
   ```

## CLI Command Examples

### 1. Convert PDF from URL to JSON (Synchronous)

Using the Arazzo runner CLI:

```bash
uvx arazzo-runner execute-operation \
  --openapi-path ./openapi/docling.json \
  --operation-id process_url_v1_convert_source_post \
  --server-variables '{"DOCLING_SERVER": "http://127.0.0.1:5001"}' \
  --inputs '{
    "sources": [
      {
        "kind": "http",
        "url": "https://arxiv.org/pdf/2206.01062"
      }
    ],
    "options": {
      "to_formats": ["json", "md"],
      "ocr": false,
      "pdf_backend": "dlparse_v2",
      "table_mode": "fast"
    },
    "target": {
      "kind": "inbody"
    }
  }'
```

**Note**: The OpenAPI spec needs a `servers` field. If missing, you'll need to add it or use server-variables.

### 2. Convert PDF from File

For file uploads, use the file operation:

```bash
uvx arazzo-runner execute-operation \
  --openapi-path ./openapi/docling.json \
  --operation-id process_file_v1_convert_file_post \
  --server-variables '{"DOCLING_SERVER": "http://127.0.0.1:5001"}' \
  --inputs '{
    "files": ["/path/to/document.pdf"],
    "from_formats": ["pdf"],
    "to_formats": ["json"],
    "target_type": "inbody",
    "do_ocr": true,
    "do_table_structure": true
  }'
```

### 3. Using Python Script

For easier testing without authentication, use the provided Python script:

```bash
# With default PDF URL
python docling_execute_example.py

# With custom PDF URL
python docling_execute_example.py "https://arxiv.org/pdf/2206.01062"
```

## Operation IDs Available

Based on the Docling OpenAPI spec:

- `process_url_v1_convert_source_post` - Convert from URL (synchronous)
- `process_url_async_v1_convert_source_async_post` - Convert from URL (async)
- `process_file_v1_convert_file_post` - Convert from file (synchronous)
- `process_file_async_v1_convert_file_async_post` - Convert from file (async)
- `task_status_v1_status_poll_task_id_get` - Get task status
- `task_result_v1_result_task_id_get` - Get task result

## Request Body Structure

### Convert from URL

```json
{
  "sources": [
    {
      "kind": "http",
      "url": "https://example.com/document.pdf"
    }
  ],
  "options": {
    "to_formats": ["json", "md"],
    "ocr": false,
    "pdf_backend": "dlparse_v2",
    "table_mode": "fast"
  },
  "target": {
    "kind": "inbody"
  }
}
```

### Convert from File

```json
{
  "files": ["<file_bytes_or_path>"],
  "from_formats": ["pdf"],
  "to_formats": ["json"],
  "target_type": "inbody",
  "do_ocr": true,
  "do_table_structure": true
}
```

## Response Structure

```json
{
  "document": {
    "json_content": {
      "content": [...]
    },
    "md_content": "...",
    "html_content": "...",
    "text_content": "..."
  },
  "status": "success",
  "processing_time": 28.15,
  "errors": []
}
```

## Troubleshooting

### Missing Servers Field

If you get "Missing or invalid 'servers' list" error:

1. **Option 1**: Add servers to the OpenAPI spec:
   ```json
   {
     "servers": [
       {
         "url": "http://127.0.0.1:5001"
       }
     ]
   }
   ```

2. **Option 2**: Use server-variables in the CLI command (may not work if spec has no servers field)

3. **Option 3**: Use the Python script which automatically adds servers

### Authentication

By default, Docling Serve runs without authentication. If you've enabled API keys:

```bash
export DOCLING_APIKEYAUTH_TOKEN="your-api-key"
```

### Server Not Running

If testing without a server, use the Python script with MockHTTPExecutor (see `test_docling_convert.py` for example).
