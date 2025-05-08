# JEAN Memory Backend Deployment & Frontend Integration Plan

This document outlines the plan to deploy the Dockerized JEAN Memory backend service to Google Cloud Run with Google OAuth authentication, automatic API key generation, and frontend integrations.

## Phase 1: Backend API Key Generation & User Authentication

The goal of this phase is to enhance the existing authentication system to generate unique API keys for each user when they authenticate with Google OAuth.

**Steps:**

1.  **Enhance Google OAuth Flow (Backend):**
    *   Ensure `backend/app/routers/google_auth_router.py` correctly handles the OAuth callback.
    *   The `handle_oauth_callback` method should exchange the `code` for tokens, fetch user info, and use a database instance (passed during router initialization) to call `db.create_or_get_user`.
    *   This method now returns user info including the `user_id` and generated `api_key` upon successful authentication.

2.  **Google OAuth Configuration (Critical):**
    *   **Redirect URI:** The correct redirect URI pattern is `http://localhost:3005/auth/google/callback.html` for local development. This URI must be:
        *   Registered exactly under "Authorized redirect URIs" in the Google Cloud Console for the OAuth 2.0 Client ID.
        *   Set as the `GOOGLE_REDIRECT_URI` environment variable in the **root `.env` file**.
    *   **Environment Variables:** `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, and `GOOGLE_REDIRECT_URI` **must** be defined in a `.env` file in the project root directory (alongside `docker-compose.yml`). Docker Compose reads this file to inject variables into the backend service.
    *   **Client-Side Callback:** The frontend handles the callback via client-side JavaScript in `frontend/public/auth/google/callback.html`. The corresponding server-side route in `frontend/server.js` (`app.get('/auth/google/callback', ...)`) is deprecated and must remain commented out.

3.  **Add Endpoint to Generate MCP Configuration:**
    *   The endpoint `@app.get("/api/mcp-config/{user_id}")` in `backend/app/main.py` allows fetching the MCP configuration using a valid `user_id` and `api_key`.
    *   It uses the database to validate the API key against the user ID.

4.  **Frontend Integration for API Key Display & MCP Config:**
    *   The frontend (`frontend/public/auth/google/callback.html`) makes an API call to the backend (`/api/auth/google/callback`) to exchange the code.
    *   Upon successful login (receiving user info + API key from the backend), the frontend stores the user session (e.g., in localStorage).
    *   Authenticated pages (e.g., `profile.html`) display user information and fetch/display the MCP configuration using the stored `user_id` and `api_key`.

## Phase 2: Backend Deployment to Google Cloud Run

The goal of this phase is to get the existing Dockerized backend service live and accessible on Google Cloud, configured for scalability and individual user data.

**Assumptions:**
*   Google OAuth authentication has been implemented
*   API key generation is working correctly
*   The Docker image for the JEAN Memory backend exists

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
        *   Secret Manager API: `gcloud services enable secretmanager.googleapis.com`

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
    *   Build the Docker image:
        ```bash
        cd backend
        docker build -t jean-memory-service:latest .
        ```
    *   Tag your local Docker image for Artifact Registry:
        ```bash
        docker tag jean-memory-service:latest YOUR_PREFERRED_REGION-docker.pkg.dev/YOUR_PROJECT_ID/YOUR_REPO_NAME/jean-memory-service:latest
        ```
        *(Example: `docker tag jean-memory-service:latest us-central1-docker.pkg.dev/my-gcp-project/jean-memory-repo/jean-memory-service:latest`)*
    *   Configure Docker to authenticate with Artifact Registry:
        ```bash
        gcloud auth configure-docker YOUR_PREFERRED_REGION-docker.pkg.dev
        ```
    *   Push the tagged image:
        ```bash
        docker push YOUR_PREFERRED_REGION-docker.pkg.dev/YOUR_PROJECT_ID/YOUR_REPO_NAME/jean-memory-service:latest
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
            --set-env-vars "^##^GOOGLE_CLIENT_ID=YOUR_PROD_CLIENT_ID##GOOGLE_CLIENT_SECRET=YOUR_PROD_SECRET##GOOGLE_REDIRECT_URI=YOUR_PROD_REDIRECT_URI##DATABASE_URL=YOUR_PROD_DB_STRING##GEMINI_API_KEY=YOUR_GEMINI_KEY##DEV_MODE=false" \
            --port YOUR_CONTAINER_PORT
        ```
    *   **Key Parameters & Production Env Vars:**
        *   `YOUR_SERVICE_NAME`: (e.g., `jean-memory-api`)
        *   `--allow-unauthenticated`: Allows public access. Review security implications for production. Consider using IAM or Identity Platform for frontend-backend authentication.
        *   `--set-env-vars`: **Crucial** for providing production secrets and configuration. Use Secret Manager for sensitive values like API keys, secrets, and database URLs in a real production setup instead of directly in the command.
            *   `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`: Your production OAuth credentials.
            *   `GOOGLE_REDIRECT_URI`: Your **production** redirect URI (e.g., `https://yourdomain.com/auth/google/callback.html`).
            *   `DATABASE_URL`: Your production database connection string.
            *   `GEMINI_API_KEY`, `CLAUDE_API_KEY`, etc.
            *   `DEV_MODE=false`: **Ensure DEV_MODE is disabled in production.**
        *   `YOUR_CONTAINER_PORT`: (e.g., `8000`).

6.  **Initial Testing & Verification:**
    *   Access the URL provided by Cloud Run.
    *   Test the production OAuth flow (requires updating Google Cloud Console with production URIs).
    *   Perform API calls to test core functionalities.
    *   Check Cloud Run logs.

## Phase 3: Frontend Deployment

1.  **Update Frontend for Production:**
    *   Build and push the frontend Docker image (steps are similar to backend).

2.  **Deploy Frontend to Cloud Run (or Vercel/other):**
    *   If deploying to Cloud Run:
        ```bash
        gcloud run deploy YOUR_FRONTEND_SERVICE_NAME \
            --image=YOUR_GCR_REGION-docker.pkg.dev/YOUR_PROJECT_ID/YOUR_REPO_NAME/jean-memory-frontend:latest \
            --platform=managed \
            --region=YOUR_GCR_REGION \
            --allow-unauthenticated \
            --set-env-vars="PORT=3005,BACKEND_URL=https://YOUR_BACKEND_SERVICE_URL" 
        ```
        *(Replace `YOUR_FRONTEND_SERVICE_NAME`, `YOUR_GCR_REGION`, `YOUR_PROJECT_ID`, `YOUR_REPO_NAME`, and the production `BACKEND_URL`)*

## Phase 4: Integration with Claude Desktop / MCP Clients

Once deployed, the integration workflow will be:

1.  **User Authentication:**
    *   User visits the deployed JEAN Memory frontend (e.g., `https://yourdomain.com`).
    *   Signs in with Google OAuth (using the production redirect URI).
    *   Upon successful authentication, the frontend displays their MCP configuration (fetched from the deployed backend using their `user_id` and `api_key`).

2.  **MCP Client Integration:**
    *   User copies their MCP configuration.
    *   Pastes the configuration into their AI client (Claude Desktop, Cursor, etc.).
    *   The MCP configuration should contain the **production backend URL** and the user-specific API key and User ID.
    *   The client can now make authenticated requests to the user's memory via the deployed backend API.

## Phase 5: OAuth Troubleshooting Summary (Reference)

Key points identified during local development debugging:

1.  **Environment Variables:** Use a single `.env` file in the project root for Docker Compose environment variable substitution.
2.  **`redirect_uri_mismatch`:** Verify exact match between Google Cloud Console ("Authorized redirect URIs"), the `GOOGLE_REDIRECT_URI` environment variable (in root `.env`), and backend logs (`[AUTH_DEBUG]`). Allow time for Google changes to propagate.
3.  **Account-Specific Errors / Caching:** For errors on specific accounts (especially in regular browser mode), clear browser cache/cookies thoroughly and try removing app permissions from the Google Account settings.
4.  **Client-Side Callback:** The frontend (`callback.html`) handles the callback; the server-side Express route (`/auth/google/callback`) is deprecated and commented out.
5.  **Duplicate Frontend Call:** A flashing error on success might indicate `callback.html` JavaScript makes a duplicate backend call. Refine the JS to call only once.

## Post-Deployment Tasks

1.  **Update Google OAuth Credentials:**
    *   Ensure the production frontend URL (e.g., `https://yourdomain.com`) is added to "Authorized JavaScript origins".
    *   Ensure the production callback URL (e.g., `https://yourdomain.com/auth/google/callback.html`) is added to "Authorized redirect URIs".
    *   Review and configure the OAuth consent screen appropriately for production.

2. **Security Enhancements:**
   * Set up Cloud Run services with proper IAM roles rather than public access
   * Configure firewall rules as needed
   * Implement API key rotation policy

3. **Monitoring and Maintenance:**
   * Set up Cloud Monitoring for CPU/memory usage and error tracking
   * Create alerting policies for critical errors
   * Implement logging for security and debugging
   * Schedule database backups 