#!/bin/bash
# JEAN Memory Deployment Script
# This script automates the deployment of JEAN Memory to Google Cloud Run

set -e  # Exit immediately if a command exits with a non-zero status

# Colors for better output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration - Edit these values
PROJECT_ID="" # Your GCP project ID
REGION="us-central1" # GCP region
REPO_NAME="jean-memory-repo" # Artifact Registry repo name
DB_INSTANCE_NAME="jean-memory-db" # Cloud SQL instance name
DB_PASSWORD="" # Secure password for database
GEMINI_API_KEY="" # Your Gemini API key
GOOGLE_CLIENT_ID="" # Your Google OAuth client ID
GOOGLE_CLIENT_SECRET="" # Your Google OAuth client secret

# Function to print colorful messages
print_message() {
  echo -e "${BLUE}[$(date +'%Y-%m-%dT%H:%M:%S%z')]${NC} $1"
}

print_error() {
  echo -e "${RED}[$(date +'%Y-%m-%dT%H:%M:%S%z')] ERROR:${NC} $1"
}

print_success() {
  echo -e "${GREEN}[$(date +'%Y-%m-%dT%H:%M:%S%z')] SUCCESS:${NC} $1"
}

# Check for required tools
check_prerequisites() {
  print_message "Checking prerequisites..."
  
  # Check if gcloud is installed
  if ! command -v gcloud &> /dev/null; then
    print_error "gcloud is not installed. Please install it: https://cloud.google.com/sdk/docs/install"
    exit 1
  fi
  
  # Check if docker is installed
  if ! command -v docker &> /dev/null; then
    print_error "docker is not installed. Please install it: https://docs.docker.com/get-docker/"
    exit 1
  fi
  
  # Check if required configuration is provided
  if [ -z "$PROJECT_ID" ]; then
    print_error "PROJECT_ID is not set. Please edit the script to set your GCP project ID."
    exit 1
  fi
  
  if [ -z "$DB_PASSWORD" ]; then
    print_error "DB_PASSWORD is not set. Please edit the script to set a secure database password."
    exit 1
  fi
  
  if [ -z "$GEMINI_API_KEY" ]; then
    print_error "GEMINI_API_KEY is not set. Please edit the script to set your Gemini API key."
    exit 1
  fi
  
  if [ -z "$GOOGLE_CLIENT_ID" ] || [ -z "$GOOGLE_CLIENT_SECRET" ]; then
    print_error "Google OAuth credentials are not set. Please edit the script to set them."
    exit 1
  fi
  
  print_success "Prerequisites check completed."
}

# Set up Google Cloud project
setup_gcp() {
  print_message "Setting up Google Cloud project..."
  
  # Authenticate gcloud if needed
  gcloud auth login --quiet
  
  # Set active project
  gcloud config set project $PROJECT_ID
  
  # Enable required APIs
  print_message "Enabling required APIs..."
  gcloud services enable artifactregistry.googleapis.com run.googleapis.com sqladmin.googleapis.com secretmanager.googleapis.com
  
  print_success "Google Cloud project setup completed."
}

# Set up Artifact Registry for Docker images
setup_artifact_registry() {
  print_message "Setting up Artifact Registry..."
  
  # Create Docker repository
  gcloud artifacts repositories create $REPO_NAME \
    --repository-format=docker \
    --location=$REGION \
    --description="JEAN Memory Docker images"
  
  # Configure Docker to use Artifact Registry
  gcloud auth configure-docker $REGION-docker.pkg.dev
  
  print_success "Artifact Registry setup completed."
}

# Set up Cloud SQL database
setup_database() {
  print_message "Setting up Cloud SQL database..."
  
  # Create PostgreSQL instance
  gcloud sql instances create $DB_INSTANCE_NAME \
    --database-version=POSTGRES_15 \
    --tier=db-f1-micro \
    --region=$REGION \
    --root-password=$DB_PASSWORD
  
  # Create database
  gcloud sql databases create jean_memory --instance=$DB_INSTANCE_NAME
  
  # Get connection string
  CONNECTION_NAME=$(gcloud sql instances describe $DB_INSTANCE_NAME --format='value(connectionName)')
  DATABASE_URL="postgresql://postgres:${DB_PASSWORD}@/jean_memory?host=/cloudsql/${CONNECTION_NAME}"
  
  print_success "Cloud SQL database setup completed."
}

# Store secrets in Secret Manager
store_secrets() {
  print_message "Storing secrets in Secret Manager..."
  
  # Store database URL
  echo -n "$DATABASE_URL" | gcloud secrets create database-url --data-file=-
  
  # Store Gemini API key
  echo -n "$GEMINI_API_KEY" | gcloud secrets create gemini-api-key --data-file=-
  
  # Store Google OAuth credentials
  echo -n "$GOOGLE_CLIENT_ID" | gcloud secrets create google-client-id --data-file=-
  echo -n "$GOOGLE_CLIENT_SECRET" | gcloud secrets create google-client-secret --data-file=-
  
  print_success "Secrets stored in Secret Manager."
}

# Build and push Docker images
build_and_push_images() {
  print_message "Building and pushing Docker images..."
  
  # Build backend image
  print_message "Building backend image..."
  cd backend
  docker build -t jean-memory-backend:latest .
  
  # Tag for Google Artifact Registry
  docker tag jean-memory-backend:latest $REGION-docker.pkg.dev/$PROJECT_ID/$REPO_NAME/jean-memory-backend:latest
  
  # Push to Artifact Registry
  docker push $REGION-docker.pkg.dev/$PROJECT_ID/$REPO_NAME/jean-memory-backend:latest
  cd ..
  
  # Build frontend image
  print_message "Building frontend image..."
  cd frontend
  docker build -t jean-memory-frontend:latest .
  
  # Tag for Google Artifact Registry
  docker tag jean-memory-frontend:latest $REGION-docker.pkg.dev/$PROJECT_ID/$REPO_NAME/jean-memory-frontend:latest
  
  # Push to Artifact Registry
  docker push $REGION-docker.pkg.dev/$PROJECT_ID/$REPO_NAME/jean-memory-frontend:latest
  cd ..
  
  print_success "Docker images built and pushed to Artifact Registry."
}

# Deploy to Cloud Run
deploy_to_cloud_run() {
  print_message "Deploying to Cloud Run..."
  
  # Get backend service URL for frontend configuration
  BACKEND_URL=""
  
  # Deploy backend
  print_message "Deploying backend service..."
  gcloud run deploy jean-memory-backend \
    --image=$REGION-docker.pkg.dev/$PROJECT_ID/$REPO_NAME/jean-memory-backend:latest \
    --platform=managed \
    --region=$REGION \
    --allow-unauthenticated \
    --add-cloudsql-instances $PROJECT_ID:$REGION:$DB_INSTANCE_NAME \
    --set-secrets=DATABASE_URL=database-url:latest,GEMINI_API_KEY=gemini-api-key:latest,GOOGLE_CLIENT_ID=google-client-id:latest,GOOGLE_CLIENT_SECRET=google-client-secret:latest \
    --set-env-vars="JEAN_API_BASE_URL=https://jean-memory-backend-xxxx-uc.a.run.app,LOG_LEVEL=INFO,TENANT_ISOLATION=strict"
  
  # Get the backend URL
  BACKEND_URL=$(gcloud run services describe jean-memory-backend --platform=managed --region=$REGION --format='value(status.url)')
  print_message "Backend URL: $BACKEND_URL"
  
  # Update Google OAuth redirect URI in Secret Manager
  FRONTEND_URL=""
  GOOGLE_REDIRECT_URI="${BACKEND_URL}/api/auth/google/callback"
  echo -n "$GOOGLE_REDIRECT_URI" | gcloud secrets create google-redirect-uri --data-file=-
  
  # Deploy frontend
  print_message "Deploying frontend service..."
  gcloud run deploy jean-memory-frontend \
    --image=$REGION-docker.pkg.dev/$PROJECT_ID/$REPO_NAME/jean-memory-frontend:latest \
    --platform=managed \
    --region=$REGION \
    --allow-unauthenticated \
    --set-env-vars="PORT=3005,BACKEND_URL=${BACKEND_URL}"
  
  # Get the frontend URL
  FRONTEND_URL=$(gcloud run services describe jean-memory-frontend --platform=managed --region=$REGION --format='value(status.url)')
  print_message "Frontend URL: $FRONTEND_URL"
  
  print_success "Deployment to Cloud Run completed."
  
  print_message "⚠️ IMPORTANT: You need to update your Google OAuth credentials in the Google Cloud Console:"
  print_message "1. Go to https://console.cloud.google.com/apis/credentials"
  print_message "2. Edit your OAuth 2.0 Client ID"
  print_message "3. Add these authorized redirect URIs:"
  print_message "   - ${BACKEND_URL}/api/auth/google/callback"
  print_message "   - ${FRONTEND_URL}/auth/google/callback"
  print_message "4. Add these authorized JavaScript origins:"
  print_message "   - ${FRONTEND_URL}"
}

# Main execution flow
main() {
  print_message "Starting JEAN Memory deployment to Google Cloud Run..."
  
  check_prerequisites
  setup_gcp
  setup_artifact_registry
  setup_database
  store_secrets
  build_and_push_images
  deploy_to_cloud_run
  
  print_success "🎉 JEAN Memory deployment completed!"
  print_message "Frontend: ${FRONTEND_URL}"
  print_message "Backend: ${BACKEND_URL}"
}

# Run the main function
main 