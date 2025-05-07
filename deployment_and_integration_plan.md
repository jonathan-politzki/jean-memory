# JEAN Memory Backend Deployment & Frontend Integration Plan

This document outlines the plan to deploy the Dockerized JEAN Memory backend service to Google Cloud Run and prepare for frontend integrations, specifically for Obsidian and GitHub.

## Phase 1: Backend Deployment to Google Cloud Run

The goal of this phase is to get the existing Dockerized backend service live and accessible on Google Cloud, configured for scalability and individual user data.

**Assumptions:**
*   A Docker image for the JEAN Memory backend already exists.
*   You have a Google Cloud Platform (GCP) account and project.

**Steps:**

1.  **Prerequisites & GCP Setup:**
    *   Install and Authenticate Google Cloud SDK (`gcloud`):
        *   Install if not present: [Google Cloud SDK Installation Guide](https://cloud.google.com/sdk/docs/install)
        *   Authenticate: `gcloud auth login`
        *   Set active project: `gcloud config set project YOUR_PROJECT_ID`
    *   Enable Required GCP APIs:
        *   Artifact Registry API: `gcloud services enable artifactregistry.googleapis.com`
        *   Cloud Run API: `gcloud services enable run.googleapis.com`
        *   Cloud SQL Admin API (if using Cloud SQL): `gcloud services enable sqladmin.googleapis.com`

2.  **Container Registry Setup (Artifact Registry):**
    *   Create a Docker repository in Artifact Registry:
        ```bash
        gcloud artifacts repositories create YOUR_REPO_NAME \
            --repository-format=docker \
            --location=YOUR_PREFERRED_REGION \
            --description="JEAN Memory Docker images"
        ```
        *(Replace `YOUR_REPO_NAME` and `YOUR_PREFERRED_REGION` e.g., `jean-memory-repo`, `us-central1`)*

3.  **Tag & Push Docker Image:**
    *   Tag your local Docker image for Artifact Registry:
        ```bash
        docker tag YOUR_LOCAL_IMAGE_NAME YOUR_PREFERRED_REGION-docker.pkg.dev/YOUR_PROJECT_ID/YOUR_REPO_NAME/YOUR_IMAGE_NAME:latest
        ```
        *(Example: `docker tag jean-memory-service us-central1-docker.pkg.dev/my-gcp-project/jean-memory-repo/jean-memory-service:latest`)*
    *   Configure Docker to authenticate with Artifact Registry:
        ```bash
        gcloud auth configure-docker YOUR_PREFERRED_REGION-docker.pkg.dev
        ```
    *   Push the tagged image:
        ```bash
        docker push YOUR_PREFERRED_REGION-docker.pkg.dev/YOUR_PROJECT_ID/YOUR_REPO_NAME/YOUR_IMAGE_NAME:latest
        ```

4.  **Database Setup (e.g., Cloud SQL):**
    *   Provision a managed database instance (e.g., Google Cloud SQL for PostgreSQL or MySQL).
    *   Create necessary databases, users, and schemas required by the JEAN Memory application.
    *   Securely note the database connection string (user, password, host, port, database name).
    *   Ensure network connectivity between Cloud Run and the database (e.g., public IP with strong credentials, Cloud SQL Proxy, or VPC native connector).

5.  **Deploy to Google Cloud Run:**
    *   Execute the deployment command:
        ```bash
        gcloud run deploy YOUR_SERVICE_NAME \
            --image YOUR_PREFERRED_REGION-docker.pkg.dev/YOUR_PROJECT_ID/YOUR_REPO_NAME/YOUR_IMAGE_NAME:latest \
            --platform managed \
            --region YOUR_PREFERRED_REGION \
            --allow-unauthenticated \
            --set-env-vars GEMINI_API_KEY="YOUR_GEMINI_API_KEY",DATABASE_URL="YOUR_DATABASE_CONNECTION_STRING" \
            --port YOUR_CONTAINER_PORT
        ```
    *   **Key Parameters:**
        *   `YOUR_SERVICE_NAME`: (e.g., `jean-memory-api`)
        *   `--allow-unauthenticated`: Allows public access for initial testing. Review for production.
        *   `--set-env-vars`: **Crucial** for providing `GEMINI_API_KEY` and `DATABASE_URL`.
        *   `YOUR_CONTAINER_PORT`: The port your application listens on inside the container (e.g., `8000`).

6.  **Initial Testing & Verification:**
    *   Access the URL provided by Cloud Run after successful deployment.
    *   Perform API calls to test core functionalities:
        *   Memory creation (`create_jean_memory_entry`)
        *   Memory access (`access_jean_memory`)
        *   Ensure `user_id` based data isolation is working.
    *   Check Cloud Run logs for any errors.

## Phase 2: Frontend Integration (Obsidian & GitHub)

The goal of this phase is to develop a frontend application that interacts with the deployed JEAN Memory backend to provide Obsidian and GitHub integration features.

**Considerations for Backend Support:**

1.  **API Accessibility:**
    *   The Cloud Run service deployed with `--allow-unauthenticated` will be publicly accessible via its HTTPS URL. This is the endpoint your frontend will call.
    *   For production and user data security, you will eventually want to implement proper authentication (e.g., OAuth 2.0, JWTs) on your API. Cloud Run can integrate with Identity Platform or other auth solutions.

2.  **CORS (Cross-Origin Resource Sharing):**
    *   If your frontend is served from a different domain than your Cloud Run service URL, you will need to configure CORS on your backend (within your FastMCP application).
    *   This typically involves setting headers like `Access-Control-Allow-Origin`, `Access-Control-Allow-Methods`, and `Access-Control-Allow-Headers`. Many Python web frameworks have middleware or extensions for handling CORS.

3.  **API Design for Frontend Needs:**
    *   Review existing API endpoints (`create_jean_memory_entry`, `access_jean_memory`, etc.) to ensure they are suitable for frontend consumption.
    *   Consider if new, specific endpoints are needed for the Obsidian and GitHub integrations (e.g., an endpoint to trigger a GitHub repo scan and store summaries, or an endpoint to fetch notes formatted for Obsidian).
    *   User authentication and authorization will be critical. The frontend will need to pass user identity (e.g., `user_id` obtained after login) to the backend.

4.  **Frontend Development:**
    *   Choose your frontend stack (React, Vue, Angular, Svelte, etc.).
    *   Implement UI/UX for interacting with Obsidian (e.g., selecting notes/vaults) and GitHub (e.g., linking repositories, specifying branches/folders).
    *   Develop logic to make authenticated API calls to the JEAN Memory backend on Cloud Run.

**Workflow Example (Frontend -> Backend for GitHub Integration):**

1.  User authenticates on the frontend. Frontend obtains a `user_id` and an auth token.
2.  User initiates a "Sync GitHub Repo" action on the frontend.
3.  Frontend makes an API call to the deployed JEAN Memory backend (e.g., `POST /integrations/github/sync`):
    *   Includes `user_id` and any necessary GitHub-specific parameters (repo URL, auth details for GitHub API if managed server-side).
    *   Includes the auth token for the JEAN Memory API.
4.  Backend receives the request:
    *   Authenticates/Authorizes the request using the token.
    *   Uses the `user_id` to scope operations.
    *   Interacts with the GitHub API (potentially using a GitHub App or OAuth token provided by the user).
    *   Processes data from GitHub (e.g., reads file contents, commit messages).
    *   Uses `create_jean_memory_entry` internally to store relevant information, associating it with the `user_id`.
5.  Backend responds to the frontend with success/failure.

## Next Steps (Post-Deployment):

*   Set up a CI/CD pipeline (e.g., using Google Cloud Build) for automated deployments of the backend.
*   Implement robust logging and monitoring using Cloud Logging and Cloud Monitoring.
*   Secure API keys and database credentials using Secret Manager.
*   Plan and implement a proper authentication and authorization layer for your API.
*   Begin frontend development. 