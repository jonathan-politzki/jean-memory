# JEAN Memory Deployment & Integration Plan (Updated May 14, 2025)

This document outlines the plan and progress for deploying the JEAN Memory backend and frontend services to Google Cloud Run, including database setup, authentication, and secure access configuration.

**Current Status:**
*   Backend (`jean-memory-api`) is deployed to Cloud Run, functional, connected to Cloud SQL, and **requires authenticated invocation**. Direct public access is blocked by Organization Policy.
*   Frontend (`jean-memory-frontend`) is deployed to Cloud Run and functional via `https://app.jeantechnologies.com`. Access is secured by Google Cloud Load Balancer and Identity-Aware Proxy (IAP).
*   **Architecture:** The frontend (`server.js`) acts as an authenticated proxy for API calls to the backend. Client-side JavaScript calls relative API paths (e.g., `/api/...`), which are handled by `server.js`. `server.js` then makes authenticated calls to the backend service (`https://jean-memory-api-...run.app`) using its Cloud Run service identity.
*   Direct browser access to default Cloud Run `.run.app` URLs remains **blocked** (403 Forbidden).
*   The primary domain `jeantechnologies.com` continues to point to Vercel. The Jean application is accessed via the subdomain `app.jeantechnologies.com`.

**Next Major Goal:** Phase 6: Final Integrations & Testing.

---

## Phase 1: Local Setup & Prerequisites (Completed)

*   **Google OAuth Flow:** Implemented in backend (`/api/auth/google/...`) and frontend (`/auth/google/callback.html` client-side handling).
*   **Dockerization:** Backend (`./backend/Dockerfile`) and frontend (`./frontend/Dockerfile`) are containerized.
*   **Local Testing:** Assumed successful via `docker-compose.yml`.

---

## Phase 2: GCP Environment Setup (Completed)

*   **Google Cloud SDK (`gcloud`):**
    *   Installed on macOS (`arm64`).
    *   Authenticated via `gcloud auth login`.
    *   PATH configuration required manual sourcing (`source ~/.zshrc` / new terminal) and explicit path (`~/google-cloud-sdk/bin/gcloud`) for some commands initially. Homebrew setup (`brew install postgresql`) eventually resolved PATH for `psql`.
*   **Project Selection:**
    *   Selected existing project `gen-lang-client-0888810452`.
*   **API Enabling:** Enabled the following APIs for the project:
    *   Artifact Registry API (`artifactregistry.googleapis.com`)
    *   Cloud Run API (`run.googleapis.com`)
    *   Cloud SQL Admin API (`sqladmin.googleapis.com`)
    *   Secret Manager API (`secretmanager.googleapis.com`)
    *   Cloud SQL Component API (`sql-component.googleapis.com`) (Enabled during deploy)
    *   Cloud Build API (`cloudbuild.googleapis.com`) (Enabled during accidental source deploy attempt)
*   **Artifact Registry Repository Creation:**
    *   Created Docker repository `jean-memory-repo` in region `us-central1`.

---

## Phase 3: Backend Deployment (`jean-memory-api`) (Completed)

*   **Docker Image Build:**
    *   Built image using `--platform linux/amd64` flag to ensure compatibility with Cloud Run execution environment.
    *   Tagged as `jean-memory-service:latest`.
*   **Docker Authentication:**
    *   Configured Docker authentication for Artifact Registry using `gcloud auth configure-docker us-central1-docker.pkg.dev`.
    *   Encountered and resolved `docker-credential-gcloud not in system PATH` issue by prepending `PATH=$HOME/google-cloud-sdk/bin:$PATH` to the `docker push` command.
*   **Image Push:** Pushed `amd64` image `us-central1-docker.pkg.dev/gen-lang-client-0888810452/jean-memory-repo/jean-memory-service:latest` to Artifact Registry.
*   **Cloud SQL Instance Creation:**
    *   Created PostgreSQL 15 instance `jean-memory-db` in `us-central1`.
    *   Instance Public IP: `35.222.241.168` (Note: Prefer connection via Cloud SQL Connection Name).
    *   Instance Connection Name: `gen-lang-client-0888810452:us-central1:jean-memory-db`
*   **Database User Creation:**
    *   Set a strong password for the default `postgres` superuser via `gcloud sql users set-password`.
    *   Created a dedicated application user `jean_app_user` with a strong password via `gcloud sql users create ... --password='...'`. Password required URL-encoding for use in `DATABASE_URL`.
*   **Database Permissions:**
    *   Connected to Cloud SQL instance via `gcloud beta sql connect ... --user=postgres`.
    *   Granted necessary privileges (`CONNECT`, `USAGE`, `ALL PRIVILEGES` on tables/sequences in `public` schema) to `jean_app_user`.
*   **Database Migrations:**
    *   Applied migrations from `backend/app/database/migrations/003_integrations.sql` by piping the file into `gcloud beta sql connect ... < backend/app/database/migrations/003_integrations.sql`.
*   **Cloud Run Deployment (`jean-memory-api`):**
    *   Deployed service using the pushed `amd64` image.
    *   Initially configured **without** `--allow-unauthenticated`.
    *   Temporarily deployed **with** `--allow-unauthenticated` during troubleshooting, but attempts to grant `allUsers` the `run.invoker` role failed due to **Organization Policy restrictions**.
    *   Final deployment configuration **requires authentication** (no `--allow-unauthenticated`).
    *   Added Cloud SQL connection using `--add-cloudsql-instances=gen-lang-client-0888810452:us-central1:jean-memory-db`.
    *   Set environment variables via `--set-env-vars`, including `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`, `GEMINI_API_KEY`, and `DATABASE_URL`.
*   **Backend Testing:** Direct calls require authentication. Authenticated inter-service calls (e.g., from frontend proxy) work.

---

## Phase 4: Frontend Deployment (`jean-memory-frontend`) & Access Troubleshooting (Completed - Deployed and Accessible via Proxy Architecture)

*   Docker Image Build:
    *   Built image using `--platform linux/amd64` flag.
    *   Tagged as `jean-memory-frontend:latest`.
*   Image Push: Pushed `amd64` image `us-central1-docker.pkg.dev/gen-lang-client-0888810452/jean-memory-repo/jean-memory-frontend:latest` to Artifact Registry.
*   Cloud Run Deployment (`jean-memory-frontend`): Deployed requiring authentication, with `BACKEND_URL` and `NODE_ENV` environment variables set.
*   **Frontend Proxy Implementation:**
    *   Modified `frontend/server.js` to act as an API proxy for requests to `/api/*`.
    *   `server.js` uses `google-auth-library` to fetch an identity token for the backend service (`ACTUAL_BACKEND_URL`).
    *   It forwards API requests from the client browser to the backend service, adding the `Authorization: Bearer <token>` header.
    *   Modified client-side JavaScript (`auth.js`, etc.) to make API calls to relative paths (e.g., `/api/auth/google/url`) instead of absolute backend URLs.
*   Access Testing and Troubleshooting Summary:
    *   Direct Browser Access to Cloud Run URL: Failed (403).
    *   `curl` with ID Token to Cloud Run URL: Successful.
    *   `gcloud run services proxy` to Cloud Run URL: Successful.
    *   IAP `400: redirect_uri_mismatch`: Resolved by adding IAP redirect URI to OAuth Client ID.
    *   IAP `The IAP service account is not provisioned...` Error: Resolved by toggling IAP Off/On and granting `Cloud Run Invoker` role to IAP service account (`service-...@gcp-sa-iap.iam.gserviceaccount.com`) via `gcloud`.
    *   **Client-side CORS / 403 Errors on API calls:** Encountered when client-side JS tried to call the backend URL (`https://jean-memory-api...`) directly.
        *   **Cause:** Organization Policy prevents making the backend service publicly invocable (`allUsers`). Therefore, direct browser calls (unauthenticated from IAM perspective) fail with 403. CORS configuration on backend was also initially missing the frontend origin.
        *   **Fix:** Implemented the frontend proxy pattern described above. Backend CORS settings updated via `backend/app/app.py` (`CORSMiddleware`). Backend redeployed requiring authentication. Frontend service account (`276083385911-compute@developer.gserviceaccount.com`) granted `Cloud Run Invoker` role for the backend service (`jean-memory-api`).
*   **Conclusion:** Secure access to `https://app.jeantechnologies.com` is working via LB+IAP. Application functionality relies on the frontend (`server.js`) proxying API calls to the authenticated backend service.

---

## Phase 5: Secure Frontend Access via IAP & Load Balancer (COMPLETED)

**Goal:** Provide secure browser access to the `jean-memory-frontend` service via `app.jeantechnologies.com`.

**Final Architecture:** User -> DNS (`app.jeantechnologies.com`) -> Google Cloud Load Balancer (Static IP: `34.160.168.171`, SSL Cert: `app-jean-memory-ssl-cert`) -> IAP (using "Jean Web Client" OAuth ID) -> Serverless NEG (`jean-frontend-serverless-neg`) -> Cloud Run Frontend (`jean-memory-frontend`) -> Frontend acts as Proxy -> Authenticated call to Cloud Run Backend (`jean-memory-api`) -> Backend uses Cloud SQL.

**Steps:** (All marked COMPLETED, notes updated)

1.  **Reserve Static External IP Address:** COMPLETED (IP: `34.160.168.171`)
2.  **Create Serverless NEG:** COMPLETED (`jean-frontend-serverless-neg` -> `jean-memory-frontend`)
3.  **Create SSL Certificate:** COMPLETED (`app-jean-memory-ssl-cert` for `app.jeantechnologies.com`, ACTIVE)
4.  **Create Load Balancer Backend Service:** COMPLETED (`jean-frontend-backend-service`)
5.  **Add NEG to Backend Service:** COMPLETED
6.  **Enable IAP on Backend Service:** COMPLETED (Referencing "Jean Web Client" OAuth ID with correct origins and redirect URIs, including the IAP handler URI)
7.  **Create Load Balancer URL Map:** COMPLETED (`jean-memory-lb-url-map` -> `jean-frontend-backend-service`)
8.  **Create Target HTTPS Proxy:** COMPLETED (`jean-memory-https-proxy` using `app-jean-memory-ssl-cert`)
9.  **Create Global Forwarding Rule:** COMPLETED
10. **Grant Necessary IAM Access:** COMPLETED
    *   User Access: `jonathan@jeantechnologies.com` granted `IAP-secured Web App User` on `jean-frontend-backend-service`.
    *   IAP Service Account Access: `service-276083385911@gcp-sa-iap.iam.gserviceaccount.com` granted `Cloud Run Invoker` at project level (via `gcloud`).
    *   Frontend->Backend Access: `276083385911-compute@developer.gserviceaccount.com` (frontend SA) granted `Cloud Run Invoker` on `jean-memory-api` service.
11. **Update DNS:** COMPLETED (A record for `app.jeantechnologies.com` -> `34.160.168.171`)
12. **Test Access:** COMPLETED (Successfully accessing `https://app.jeantechnologies.com` via IAP and frontend proxy).

---

## Phase 6: Final Integrations & Testing (Current Focus)

### Resolved Issues
* **Frontend JavaScript Configuration:** Fixed by ensuring proper configuration injection in `server.js` before serving pages.
* **CORS Configuration:** Updated `backend/app/app.py` to include `https://app.jeantechnologies.com` in allowed origins.
* **Cloud Run Authentication:** Implemented successful proxy pattern where frontend service proxies API requests with service-to-service authentication.
* **Google Auth 400 Error:** Resolved by correctly implementing authenticated proxy in `frontend/server.js` for all `/api/*` routes and modifying client-side JavaScript to use relative API paths.

### Path Forward: Next Steps

1. **Frontend UI Completion (Priority: High)**
   * Complete remaining UI components for user management
   * Implement proper loading states and error handling
   * Add comprehensive user feedback for all operations
   * Implement responsive design for mobile accessibility

2. **MCP Client Integration (Priority: High)**
   * Update Claude Desktop/MCP clients to use the authenticated backend pattern
   * Configure client authentication using:
     * Service account keys for development and testing
     * OAuth user flow for production usage
   * Implement token refresh logic in clients to prevent authentication timeouts

3. **Testing and Quality Assurance (Priority: Medium)**
   * Develop automated test suite for API endpoints
   * Create end-to-end tests for authentication flows
   * Test memory storage and retrieval with various data types
   * Performance testing under load conditions

4. **Security Improvements (Priority: High)**
   * Implement regular API key rotation
   * Configure Cloud Armor WAF rules on the Load Balancer
   * Set up alerts for suspicious access patterns
   * Conduct security review of all authentication flows

5. **Monitoring and Observability (Priority: Medium)**
   * Set up Cloud Monitoring dashboards for:
     * API latency and error rates
     * Database performance
     * Frontend performance metrics
   * Configure alerting for critical service disruptions
   * Implement structured logging for easier debugging

6. **Documentation (Priority: Medium)**
   * Update architectural diagrams to reflect current implementation
   * Document API endpoints with examples
   * Create user guide for client integration
   * Document operational procedures for maintenance

### Implementation Schedule

| Task | Timeline | Dependencies | Owner |
|------|----------|--------------|-------|
| Frontend UI Completion | 1-2 weeks | None | Frontend team |
| MCP Client Integration | 2 weeks | Stable API endpoints | Client team |
| Testing and QA | Ongoing | Feature completion | QA team |
| Security Improvements | 1 week | Core functionality working | DevOps team |
| Monitoring Setup | 3 days | Deployed services | DevOps team |
| Documentation | Ongoing | Implementation details | All teams |

### Required Resources

* Developer time for frontend completion
* QA resources for comprehensive testing
* Cloud budget for additional services (monitoring, WAF)
* Documentation resources

## Post-Deployment Tasks

1. **Update Google OAuth Credentials:**
   * Ensure the production frontend URL is added to "Authorized JavaScript origins"
   * Ensure the production callback URL is added to "Authorized redirect URIs"
   * Review and configure the OAuth consent screen appropriately for production

2. **Security Enhancements:**
   * Regularly review IAM roles and permissions
   * Implement scheduled security scans
   * Document security protocols for incident response

3. **Monitoring and Maintenance:**
   * Set up Cloud Monitoring for CPU/memory usage and error tracking
   * Create alerting policies for critical errors
   * Implement logging for security and debugging
   * Schedule database backups and test recovery procedures

## Appendix: Troubleshooting Summary Notes

*   **Architecture Mismatch:** Resolved (`--platform linux/amd64`).
*   **Docker Auth:** Resolved (`gcloud auth configure-docker`).
*   **Database Password Encoding:** Resolved (URL-encode password).
*   **Browser 403 Forbidden (Direct Cloud Run URL):** Acknowledged; resolved via LB/IAP/Proxy.
*   **`gcloud` Components:** Acknowledged.
*   **`psql` Client:** Acknowledged.
*   **Local MCP Client Setup Issues:** Resolved (Poetry path, SSL certs).
*   **IAP `redirect_uri_mismatch`:** Resolved (Added IAP handler URI to OAuth client).
*   **IAP Service Account Not Provisioned:** Resolved (Toggled IAP, granted `run.invoker` via `gcloud`).
*   **Console UI IAM Issues:** Noted difficulty adding Google-managed service accounts via UI; `gcloud` was successful.
*   **Client CORS/403 on Backend API Calls:** Resolved by implementing frontend proxy pattern due to Org Policy preventing public Cloud Run invocation.
*   **Google Auth 400 Error:** Resolved by implementing correct authentication flow in the frontend proxy