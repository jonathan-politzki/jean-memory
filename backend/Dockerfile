FROM python:3.10-slim

WORKDIR /app

# Install poetry
RUN pip install poetry==1.7.1

# Copy poetry configuration files
COPY pyproject.toml poetry.lock* /app/

# Configure poetry to not create a virtual environment
RUN poetry config virtualenvs.create false

# Install dependencies
RUN poetry install --no-interaction --no-ansi

# Explicitly install MCP SDK
RUN pip install "mcp[cli]>=1.6.0"

# Add aiohttp to Poetry dependencies and install
RUN poetry add aiohttp aiofiles

# Copy application code
COPY . /app/

# Expose ports for both servers
EXPOSE 8000 8001

# Set environment variables
ENV MCP_LOG_LEVEL=INFO
ENV MCP_LOG_TO_STDERR=true

# Command to run both servers, with Uvicorn using the PORT env variable
CMD bash -c "python jean_mcp_server.py --mode http --host 0.0.0.0 --port 8001 & python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}" 