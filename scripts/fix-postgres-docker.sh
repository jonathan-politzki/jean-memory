#!/bin/bash

echo "PostgreSQL Docker Container Diagnostic Tool"
echo "==========================================="
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
  echo "❌ Docker is not running. Please start Docker Desktop and try again."
  exit 1
fi

echo "✅ Docker is running."
echo ""

# Check if PostgreSQL container is running
PG_CONTAINER=$(docker ps | grep postgres | awk '{print $1}')

if [ -z "$PG_CONTAINER" ]; then
  echo "❌ No PostgreSQL container found. Starting PostgreSQL container..."
  docker-compose up -d postgres
  sleep 5  # Wait for container to initialize
  PG_CONTAINER=$(docker ps | grep postgres | awk '{print $1}')
  
  if [ -z "$PG_CONTAINER" ]; then
    echo "❌ Failed to start PostgreSQL container."
    exit 1
  fi
else
  echo "✅ PostgreSQL container is running: $PG_CONTAINER"
fi

echo ""
echo "Checking PostgreSQL settings..."
echo ""

# Check environment variables
echo "Environment variables:"
docker exec -it $PG_CONTAINER env | grep POSTGRES

echo ""
echo "Default PostgreSQL user:"
docker exec -it $PG_CONTAINER psql -U postgres -c "\du" 2>&1 || echo "Default 'postgres' user not available"

echo ""
echo "Creating postgres superuser if needed..."
docker exec -it $PG_CONTAINER bash -c "psql -c \"CREATE ROLE postgres WITH LOGIN SUPERUSER PASSWORD 'postgres';\" || echo 'User already exists or cannot create'" 2>&1

echo ""
echo "Testing connection with postgres user..."
docker exec -it $PG_CONTAINER psql -U postgres -c "SELECT current_user;" 2>&1

echo ""
echo "Creating jean user if needed..."
docker exec -it $PG_CONTAINER bash -c "psql -U postgres -c \"CREATE USER jean WITH PASSWORD 'jean_password';\" || echo 'User already exists or cannot create'" 2>&1
docker exec -it $PG_CONTAINER bash -c "psql -U postgres -c \"CREATE DATABASE jean;\" || echo 'Database already exists or cannot create'" 2>&1
docker exec -it $PG_CONTAINER bash -c "psql -U postgres -c \"GRANT ALL PRIVILEGES ON DATABASE jean TO jean;\" || echo 'Cannot grant privileges'" 2>&1

echo ""
echo "Diagnostic complete."
echo ""
echo "Try these connection strings in your .env file:"
echo ""
echo "# For local development (backend/.env):"
echo "DATABASE_URL=postgresql://postgres:postgres@localhost:5432/postgres"
echo ""
echo "# For Docker Compose deployment:"
echo "DATABASE_URL=postgresql://postgres:postgres@postgres:5432/postgres"
echo ""
echo "To test connection directly:"
echo "psql -h localhost -U postgres" 