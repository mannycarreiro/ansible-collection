# J2Live — Jinja2 Live Parser & Renderer

A modern, real-time Jinja2 template renderer with a sleek dark/light UI.  
Inspired by [j2live.ttl255.com](https://j2live.ttl255.com).

---

## 🚀 Quick Start

### With Docker Compose (recommended)

```bash
# Clone / enter project directory
cd j2live

# Build and start both services
docker compose up --build

# Open in browser
open http://localhost:8080
```

- **Frontend**: http://localhost:8080
- **Backend API**: http://localhost:5000

---

## 🏗️ Architecture

```
j2live/
├── backend/
│   ├── app.py           # Flask API (Jinja2 rendering engine)
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── index.html       # Single-file SPA (Tailwind + CodeMirror)
│   ├── nginx.conf       # Nginx reverse proxy config
│   └── Dockerfile
└── docker-compose.yml
```

| Service    | Port | Description                           |
|------------|------|---------------------------------------|
| `frontend` | 8080 | Nginx serving the SPA + proxying /api |
| `backend`  | 5000 | Flask/Gunicorn Jinja2 render API      |

---

## ✨ Features

- **Real-time rendering** — auto-renders as you type (400ms debounce)
- **CodeMirror editors** — syntax highlighting for Jinja2, JSON, YAML
- **Dark / Light theme** — toggle in header, persisted to localStorage
- **Variable formats** — JSON or YAML variable input
- **Jinja2 options:**
  - `undefined` behavior: silent, strict, debug, chainable
  - Extensions: loopcontrols, do, debug
  - Whitespace: `trim_blocks`, `lstrip_blocks`
- **7 built-in examples** to get started quickly
- **Copy / Download** output
- **API health indicator** in header
- **Keyboard shortcut**: `Ctrl/Cmd + Enter` to render

---

## 🔌 API Reference

### `POST /render`
Render a Jinja2 template.

**Request body:**
```json
{
  "template": "Hello, {{ name }}!",
  "variables": "{\"name\": \"World\"}",
  "format": "json",
  "undefined": "undefined",
  "extensions": ["loopcontrols"],
  "trim_blocks": false,
  "lstrip_blocks": false
}
```

**Response:**
```json
{ "output": "Hello, World!", "error": null }
```

### `POST /validate`
Validate template syntax only (no rendering).

### `GET /health`
Health check endpoint.

---

## 🛠️ Development (without Docker)

**Backend:**
```bash
cd backend
pip install -r requirements.txt
python app.py
# Runs on http://localhost:5000
```

**Frontend:**
```bash
cd frontend
# Serve with any static file server
python -m http.server 8080
# Then update API_BASE in index.html to http://localhost:5000
```

---

## 🐳 Docker Commands

```bash
# Start in background
docker compose up -d --build

# View logs
docker compose logs -f

# Stop
docker compose down

# Rebuild single service
docker compose up -d --build backend
```
