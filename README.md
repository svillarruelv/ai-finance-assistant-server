# Backend - AI Finance Assistant

## 🛠️ Tech Stack

| Technology | Purpose |
|------------|---------|
| **FastAPI** | REST API framework |
| **Python 3.12** | Runtime |
| **uv** | Package management |
| **PostgreSQL** | Database |
| **Pydantic** | Data validation |
| **Docker** | Containerization |

## 📁 Project Structure

```
server/
├── app/
│   ├── api/          # API endpoints
│   ├── core/         # Exceptions, middleware
│   ├── mock/         # Sample data
│   ├── models/       # Database models
│   ├── schemas/      # Pydantic schemas
│   └── services/     # Business logic
├── Dockerfile
└── ...
```

## 💻 Local Development

1. **Navigate to the server directory:**
   ```bash
   cd server
   ```

2. **Activate environment:**
   ```bash
   source .venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   uv sync
   ```

4. **Run the application:**
   ```bash
   python run.py
   # or
   uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

## 🐳 Docker

To run the server with Docker Compose (ensure the database is running or the composed service handles it):

```bash
docker compose up -d
```

## 📄 Environment Variables

Required environment variables (in `.env` or environment):

```env
# Database
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=finance_assistant

# Server
DEBUG=true
```
