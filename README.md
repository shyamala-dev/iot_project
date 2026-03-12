# IoT Project

A Django REST API for managing user-owned IoT devices.

## Features

- JWT authentication with `djangorestframework-simplejwt`
- Per-user device listing, creation, update, and deletion
- Device status filtering

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

## Running Django

```bash
python manage.py migrate
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

## Secret Handling

- Do not commit real API keys or secrets.
- Revoke and rotate any key that was ever committed, even if it has since been removed from the latest files.
