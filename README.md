# IoT Project

A Django REST API for managing user-owned IoT devices.

## Features

- JWT authentication with `djangorestframework-simplejwt`
- Per-user device listing, creation, update, and deletion
- Device status filtering
- RAG proof of concept using Chroma plus Gemini over indexed device data

## Project Structure

- `iot_project/`: Django project settings and URL configuration
- `devices/`: device models, serializers, views, templates, and routes
- `db.sqlite3`: local development database

## Main Endpoints

- `POST /api/token/`
- `POST /api/token/refresh/`
- `GET /devices/list/`
- `GET, POST /devices/`
- `GET, PUT, PATCH, DELETE /devices/<id>/`

## Requirements

- Python 3.12
- Django
- Django REST Framework
- `djangorestframework-simplejwt`
- `chromadb`
- `google-genai`

## Setup

1. Create and activate a virtual environment.
2. Install the project dependencies.
3. Copy `.env.example` to `.env` or export the same variables in your shell.
4. Run Django migrations.
5. Start the Django app.

Example environment variables:

```bash
cp .env.example .env
set -a
source .env
set +a
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## Running Django

```bash
python manage.py migrate
python manage.py rebuild_device_rag
python manage.py runserver
```

The Django app runs on `http://127.0.0.1:8000/`.

## Authentication

Get a JWT access token:

```bash
curl -X POST http://127.0.0.1:8000/api/token/ \
  -H "Content-Type: application/json" \
  -d '{"username":"your-user","password":"your-password"}'
```

Use the returned access token:

```bash
curl http://127.0.0.1:8000/devices/ \
  -H "Authorization: Bearer <access-token>"
```

## RAG PoC

The PoC indexes each user's device records and recent sessions into a local Chroma collection, then uses Gemini for retrieval embeddings and answer generation.

Index current device data:

```bash
python manage.py rebuild_device_rag
```

Ask a question:

```bash
curl -X POST http://127.0.0.1:8000/devices/rag/query/ \
  -H "Authorization: Bearer <access-token>" \
  -H "Content-Type: application/json" \
  -d '{"question":"Which of my devices are offline?","limit":3}'
```

Browser playground:

```bash
http://127.0.0.1:8000/rag/
```

The playground lets you log in with your Django user, fetch a JWT token, submit a RAG question, and inspect the retrieved matches without using `curl`.

Optional environment variables:

```bash
GEMINI_EMBEDDING_MODEL=gemini-embedding-001
CHROMA_COLLECTION_NAME=device-knowledge
CHROMA_PERSIST_DIR=.chroma
```

## MCP PoC

This project also includes a small MCP server that exposes device data and the existing RAG flow as tools.

Install dependencies, then run:

```bash
python -m devices.mcp_server
```

The MCP server is designed as a sidecar process for any MCP-capable client. Keep client configuration local to your own machine rather than committing editor-specific config into this repo.

Run it as a stdio server from the project root:

```bash
python -m devices.mcp_server
```

Then point your client at that command. Example generic server command:

```text
python -m devices.mcp_server
```

The server exposes these tools:

- `list_devices`
- `get_device`
- `ask_devices_rag`
- `rebuild_device_index`
- `rebuild_all_device_indexes`

Example tool inputs:

```json
{"username":"your-user","status":"offline"}
```

```json
{"username":"your-user","question":"Which of my devices are offline?","limit":3}
```

## Secret Handling

- Do not commit real API keys or secrets.
- Revoke and rotate any key that was ever committed, even if it has since been removed from the latest files.
