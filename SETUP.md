# JEAN Setup Guide

This guide provides instructions for setting up and running the JEAN project using Docker.

## Prerequisites

- Docker and Docker Compose installed on your machine
- A Google Cloud Project with Gemini API access (for obtaining a Gemini API key)

## Setup Steps

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd jean-memory
   ```

2. **Configure environment variables:**
   Create a `.env` file in the root directory with the following content:
   ```
   GEMINI_API_KEY=your_gemini_api_key
   ```
   Replace `your_gemini_api_key` with your actual Gemini API key.

3. **Build and start the containers:**
   ```bash
   docker-compose up -d --build
   ```
   This will:
   - Build the backend container
   - Start a PostgreSQL database
   - Connect the services together

4. **Verify the services are running:**
   ```bash
   docker-compose ps
   ```
   You should see both the `backend` and `postgres` services running.

5. **Check the backend health:**
   ```bash
   curl http://localhost:8000/health
   ```
   Should return: `{"status":"ok"}`

## Using the Application

Currently, the backend implements an MCP server that handles `store` and `retrieve` operations. The frontend is not yet implemented.

You can interact with the MCP server directly using HTTP requests:

### Example MCP Retrieve Request:
```bash
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "method": "retrieve",
    "params": {
      "query": "What are my personal values?"
    }
  }'
```

### Example MCP Store Request:
```bash
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "method": "store",
    "params": {
      "context_type": "notes",
      "content": "Remember to buy groceries tomorrow.",
      "source_identifier": "personal-note-1"
    }
  }'
```

## Stopping the Services

To stop the running containers:
```bash
docker-compose down
```

To stop and also remove all data (including the database volume):
```bash
docker-compose down -v
```

## Development

For development work, you can run the backend without Docker:

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Install dependencies using Poetry:
   ```bash
   poetry install
   ```

3. Run the application:
   ```bash
   poetry run uvicorn app.main:app --reload
   ``` 