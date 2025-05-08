# JEAN Memory Deployment & Integration Plan (Updated May 8, 2025)

This document outlines the plan and progress for deploying the JEAN Memory backend and frontend services to Google Cloud Run, including database setup, authentication, and secure access configuration.

**Current Status:**
*   Backend (`jean-memory-api`) is deployed, functional, and connected to Cloud SQL. Requires authenticated access.
*   Frontend (`jean-memory-frontend`) is deployed and functional. Requires authenticated access.
*   Direct browser access to both services via their default `.run.app` URLs is **blocked** (results in 403 Forbidden), likely due to organization security policies, even for authenticated users with `run.invoker` roles.
*   Access via authenticated `curl` requests (using `gcloud auth print-identity-token`) **works** for both services.
*   Access to the frontend via `gcloud run services proxy` **works**, and the Google OAuth login flow was successfully tested through this proxy.

**Next Major Goal:** Configure secure browser access to the frontend using Google Cloud Load Balancer and Identity-Aware Proxy (IAP).

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
    *   Configured **without** `--allow-unauthenticated` (requires authentication).
    *   Added Cloud SQL connection using `--add-cloudsql-instances=gen-lang-client-0888810452:us-central1:jean-memory-db`.
    *   Set environment variables via `--set-env-vars`, including Google credentials, API keys, and a correctly URL-encoded `DATABASE_URL` using the Cloud SQL connection name (`postgresql://jean_app_user:ENCODED_PASSWORD@/cloudsql/gen-lang-client-0888810452:us-central1:jean-memory-db/postgres`).
*   **Backend Testing:**
    *   Verified successful authenticated access using `curl` with an ID token (`gcloud auth print-identity-token`) against the `/health` endpoint.

---

## Phase 4: Frontend Deployment (`jean-memory-frontend`) & Access Troubleshooting (Completed - Deployed, Awaiting IAP)

*   **Docker Image Build:**
    *   Built image using `--platform linux/amd64` flag.
    *   Tagged as `jean-memory-frontend:latest`.
*   **Image Push:** Pushed `amd64` image `us-central1-docker.pkg.dev/gen-lang-client-0888810452/jean-memory-repo/jean-memory-frontend:latest` to Artifact Registry.
*   **Cloud Run Deployment (`jean-memory-frontend`):**
    *   Initial attempt with `--allow-unauthenticated` completed deployment but failed to set IAM policy for `allUsers` (likely Org Policy conflict). Direct browser access failed (403).
    *   Redeployed **without** `--allow-unauthenticated` (requires authentication).
    *   Set environment variables `BACKEND_URL=https://jean-memory-api-276083385911.us-central1.run.app` and `NODE_ENV=production`. (Removed reserved `PORT` variable).
*   **Access Testing Results:**
    *   Direct Browser Access (`https://jean-memory-frontend-...`): **Consistently Failed (403 Forbidden)**, even when logged into the authorized Google account (`jonathan@...` which has `run.invoker` permission). This occurs before hitting the application code.
    *   `curl` with ID Token: **Successful** (returned `index.html` content).
    *   `gcloud run services proxy`: **Successful** (accessed via `http://localhost:8080`). Full Google OAuth login flow initiated from the proxied frontend worked successfully, interacting with the deployed backend.
*   **Conclusion:** Frontend and backend applications are functional and correctly configured for authentication. Direct browser access via default Cloud Run URLs is blocked by Google infrastructure/policy in this project environment.

---

## Phase 5: Secure Frontend Access via IAP & Load Balancer (Next Steps)

**Goal:** Provide secure browser access to the `jean-memory-frontend` service using Identity-Aware Proxy (IAP) fronted by a Google Cloud HTTPS Load Balancer.

**Steps:**

1.  **Reserve Static External IP Address:**
    *   Create a global static external IP address for the Load Balancer frontend.
    *   Command: `gcloud compute addresses create jean-memory-lb-ip --global --network-tier=PREMIUM`
    *   Note the reserved IP address.

2.  **Create Serverless NEG:**
    *   Create a Serverless Network Endpoint Group (NEG) pointing to the `jean-memory-frontend` Cloud Run service.
    *   Command: `gcloud compute network-endpoint-groups create jean-frontend-serverless-neg --region=us-central1 --network-endpoint-type=serverless --cloud-run-service=jean-memory-frontend`

3.  **Create SSL Certificate (Google-managed):**
    *   If using a custom domain (e.g., `jean.yourdomain.com`), configure DNS first.
    *   Create a Google-managed SSL certificate for your domain(s). This requires domain ownership verification.
    *   Command: `gcloud compute ssl-certificates create jean-memory-ssl-cert --domains=YOUR_DOMAIN_HERE` (Replace `YOUR_DOMAIN_HERE`)
    *   (If no custom domain, skip this and use Google's default domain for the LB initially, though SSL is still recommended).

4.  **Create Load Balancer Backend Service:**
    *   Create a backend service that will route traffic to the Serverless NEG.
    *   Command: `gcloud compute backend-services create jean-frontend-backend-service --global --load-balancing-scheme=EXTERNAL_MANAGED`

5.  **Add NEG to Backend Service:**
    *   Attach the Serverless NEG created in Step 2 to the backend service.
    *   Command: `gcloud compute backend-services add-backend jean-frontend-backend-service --global --network-endpoint-group=jean-frontend-serverless-neg --network-endpoint-group-region=us-central1`

6.  **Enable IAP on Backend Service:**
    *   **OAuth Consent Screen:** Ensure an OAuth consent screen is configured for the project (required for IAP). Navigate to "APIs & Services" -> "OAuth consent screen" in the Console. Configure internal or external as appropriate.
    *   **Enable IAP:** Use `gcloud` or the Console to enable IAP for the backend service, referencing the OAuth client ID created for web applications (ensure the Load Balancer's future URI is added there if necessary, though typically IAP uses its own redirect).
    *   Command: `gcloud compute backend-services update jean-frontend-backend-service --global --iap=enabled,oauth2-client-id=YOUR_WEB_OAUTH_CLIENT_ID,oauth2-client-secret=YOUR_WEB_OAUTH_CLIENT_SECRET` (Replace with your *actual* OAuth Web Client ID and Secret).

7.  **Create Load Balancer URL Map:**
    *   Define how incoming requests are routed to backend services (for now, default to `jean-frontend-backend-service`).
    *   Command: `gcloud compute url-maps create jean-memory-lb-url-map --default-service jean-frontend-backend-service`

8.  **Create Target HTTPS Proxy:**
    *   Create the proxy that uses the URL map and the SSL certificate.
    *   Command: `gcloud compute target-https-proxies create jean-memory-https-proxy --url-map=jean-memory-lb-url-map --ssl-certificates=jean-memory-ssl-cert` (Reference the cert created in Step 3, if applicable).

9.  **Create Global Forwarding Rule:**
    *   Create the rule that directs traffic from the reserved static IP address and port 443 to the HTTPS proxy.
    *   Command: `gcloud compute forwarding-rules create jean-memory-https-forwarding-rule --global --load-balancing-scheme=EXTERNAL_MANAGED --network-tier=PREMIUM --address=jean-memory-lb-ip --target-https-proxy=jean-memory-https-proxy --ports=443`

10. **Grant Users IAP Access:**
    *   Grant users/groups who need browser access the `IAP-secured Web App User` (`roles/iap.securedWebAppUser`) role *on the IAP-secured backend service*.
    *   Command: `gcloud compute backend-services add-iam-policy-binding jean-frontend-backend-service --global --member='user:jonathan@jeantechnologies.com' --role='roles/iap.securedWebAppUser'`

11. **Update DNS (If using Custom Domain):**
    *   Point your custom domain's A record to the reserved static IP address noted in Step 1.

12. **Test Access:**
    *   Access the frontend via the Load Balancer's IP address or your custom domain (if configured).
    *   You should be redirected through the Google login flow (handled by IAP).
    *   After successful login, you should see your frontend application.

---

## Phase 6: Final Integrations & Testing (Future)

*   **MCP Client Integration:**
    *   Update Claude Desktop/MCP clients with the production backend URL (`https://jean-memory-api-...`) and user-specific API key/User ID obtained from the frontend.
    *   Determine how MCP clients will authenticate to the *backend* service (which requires authentication). Options:
        *   Configure clients to obtain and send Google ID Tokens (ideal if possible).
        *   Potentially place the *backend* service behind IAP as well (requires clients to handle IAP flow or use service account authentication).
        *   Explore API Gateway for more granular API key management/authentication.
*   **Thorough End-to-End Testing:** Test all features, data sources, and integrations.
*   **Security Enhancements:** Review IAM roles, consider API key rotation, enable Cloud Armor WAF rules on the Load Balancer.
*   **Monitoring & Maintenance:** Set up Cloud Monitoring dashboards, alerting policies, logging for Cloud Run/Cloud SQL/Load Balancer, configure database backups.

---

## Appendix: Troubleshooting Summary Notes

*   **Architecture Mismatch:** Initial backend deployment failed (`exec format error`) due to building `arm64` image on Mac for `amd64` Cloud Run. Resolved by adding `--platform linux/amd64` to `docker build`.
*   **Docker Auth:** `docker push` initially failed (`Unauthenticated`) due to `docker-credential-gcloud` not found in PATH. Resolved by prepending SDK `bin` directory to `PATH` for the `docker push` command.
*   **Database Password Encoding:** Application failed to connect to DB (`ValueError: bad query field`) because password contained special characters (`!`, `?`). Resolved by URL-encoding the password in the `DATABASE_URL` environment variable.
*   **Browser 403 Forbidden:** Persistent issue accessing deployed services directly via browser (`.run.app` URL) despite correct IAM (`run.invoker`) and successful authenticated `curl` requests. Likely caused by restrictive Organization Policy or similar Google infrastructure behavior preventing direct authenticated browser access. Workaround is using IAP + Load Balancer.
*   **`gcloud` Components:** Required installation of `beta` and `cloud_sql_proxy` components for certain commands (`gcloud beta sql connect`, `gcloud run services proxy`).
*   **`psql` Client:** Required installation via Homebrew (`brew install postgresql`) for `gcloud beta sql connect` to function.

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