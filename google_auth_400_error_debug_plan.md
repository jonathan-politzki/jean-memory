# JEAN Memory - Google Authentication 400 Error Debug Plan

**Last Updated:** May 15, 2025

## 1. Problem Overview

The application is experiencing a persistent "400 Bad Request" error during the Google OAuth flow. Specifically, when the frontend (`jean-memory-frontend`) attempts to get the Google Auth URL from the backend (`jean-memory-service` or `jean-memory-api`) via a proxied request, the backend responds with a 400 error.

**URL where error occurs (example):** `https://app.jeantechnologies.com/api/auth/google/url?user_id=temp-xxxxxxxxxxx`

This error prevents users from initiating the Google login process, falling back to a demo login. The core issue seems to be with the request made from the frontend proxy to the backend API endpoint `/api/auth/google/url`.

## 2. System Architecture Relevant to the Issue

*   **Frontend (`jean-memory-frontend`):**
    *   Cloud Run service.
    *   Serves static HTML/JS/CSS.
    *   Contains `frontend/server.js` which acts as an authenticated proxy for all `/api/*` calls to the backend.
    *   `server.js` uses `google-auth-library` to fetch an identity token for the backend service.
    *   Client-side JavaScript (`auth.js`) calls relative API paths (e.g., `/api/auth/google/url`).
    *   Publicly accessible via `https://app.jeantechnologies.com` (Load Balancer + IAP).
*   **Backend (`jean-memory-service` / `jean-memory-api` - Naming seems interchangeable in logs/docs):**
    *   Cloud Run service.
    *   Requires authenticated invocation (IAM).
    *   `backend/Dockerfile` runs two processes:
        *   `python jean_mcp_server.py --mode http --host 0.0.0.0 --port 8001`
        *   `python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}` (This is the FastAPI app serving `/api/...`)
    *   Connected to Cloud SQL.
    *   Environment variable `BACKEND_URL` in the frontend service points to this backend service\'s Cloud Run URL (e.g., `https://jean-memory-service-xxxxxxxxxx.us-central1.run.app`).

## 3. What We Know & What We\'ve Tried

### 3.1. Confirmed Working Components:

*   **Frontend to Backend IAM Authentication:**
    *   The frontend service account (`276083385911-compute@developer.gserviceaccount.com`) has the `roles/run.invoker` permission on the backend service (`jean-memory-service`). This allows the frontend proxy to make authenticated calls to the backend.
    *   `frontend/server.js` successfully fetches an ID token for the backend service audience.
*   **Backend Service Startup:**
    *   The `jean-memory-service` (backend) starts up, and logs indicate the Uvicorn server (FastAPI) is running on port 8080 and the `GoogleAuthRouter` is initialized.
    *   Relevant backend logs:
        *   `INFO: Uvicorn running on http://0.0.0.0:8080 (Press CTRL+C to quit)`
        *   `INFO: Application startup complete.`
        *   `INFO - GoogleAuthRouter initialized. Client ID set: True, Redirect URI: https://app.jeantechnologies.com/auth/google/callback.html`
*   **Frontend Proxy Logging:**
    *   `frontend/server.js` logs indicate it\'s attempting to proxy requests to the correct backend URL and path.
    *   It logs the ID token length, suggesting a token is being obtained.
    *   It logs the 400 status received from the backend but often lacks the detailed error *body* from the backend.

### 3.2. Attempts to Fix & Learnings:

*   **Dockerfile `CMD` Restoration:**
    *   **Action:** Ensured the `backend/Dockerfile` `CMD` runs both `jean_mcp_server.py` and `uvicorn app.main:app`.
    *   **Result:** Backend logs confirm both processes seem to start. The Uvicorn app is serving on `${PORT:-8080}`. This was a necessary fix but didn\'t resolve the 400.
*   **ID Token Audience in `frontend/server.js`:**
    *   **Action:** Modified `frontend/server.js` to use `new URL(ACTUAL_BACKEND_URL).origin` as the audience for fetching the ID token, instead of the full `ACTUAL_BACKEND_URL`.
    *   **Result:** This is the correct approach for service-to-service authentication ID tokens. The frontend successfully obtains a token for this audience. Did not resolve the 400.
*   **IAM Permissions for Frontend SA:**
    *   **Action:** Verified and re-applied `roles/run.invoker` for the frontend service account (`276083385911-compute@developer.gserviceaccount.com`) on the `jean-memory-service`.
    *   **Result:** Confirmed via `gcloud run services get-iam-policy` that the binding is active. Necessary for the proxy to call the backend, but the 400 persists.
*   **Redeployment of Services:**
    *   **Action:** Both frontend and backend services were redeployed after changes.
    *   **Result:** Ensured changes were live. No change in 400 error.
*   **Enhanced Logging in `frontend/server.js`:**
    *   **Action:** Added more `console.log` and `console.error` statements in the proxy logic in `frontend/server.js` to see headers and the body of error responses from the backend.
    *   **Result:** Confirmed the 400 status is coming from the backend. However, the *detailed error message/reason* from the backend\'s FastAPI application (e.g., Pydantic validation error, missing parameter) is not always clearly captured or logged by the frontend proxy, making it hard to pinpoint the exact cause within the backend\'s `/api/auth/google/url` endpoint.
*   **`user_id` Parameter:**
    *   The request being made is `GET /api/auth/google/url?user_id=temp-xxxxxxxxxxx`.
    *   It\'s unclear if the backend endpoint `/api/auth/google/url` actually *uses* or *requires* the `user_id` query parameter, or if its presence/absence/format is causing an issue.

### 3.3. Key Log Snippets (Illustrative):

*   **Frontend Browser Console (Error):**
    ```
    GET https://app.jeantechnologies.com/api/auth/google/url?user_id=temp-xxxxxxxxxxx 400 (Bad Request)
    Proxied backend call returned status: 400
    Google authentication setup failed via proxy. Falling back to demo login.
    ```
*   **Frontend `server.js` Logs (Illustrative - from previous debugging attempts):**
    ```
    Proxying request: GET /api/auth/google/url?user_id=temp-xxxxxxxxxxx -> https://jean-memory-service-xxxxxxxxxx.us-central1.run.app/api/auth/google/url?user_id=temp-xxxxxxxxxxx
    Fetching ID token client for target audience: https://jean-memory-service-xxxxxxxxxx.us-central1.run.app
    Successfully created ID token client.
    Got ID token for https://jean-memory-service-xxxxxxxxxx.us-central1.run.app (length: xxxx)
    Request headers being sent to backend: { Authorization: \'Bearer eyJhbGciOiJSUzI1NiIsImtpZCI6ImY......\' }
    Backend response status for /api/auth/google/url?user_id=temp-xxxxxxxxxxx: 400
    ERROR - Backend response for /api/auth/google/url?user_id=temp-xxxxxxxxxxx (status 400): {"detail":"[Specific error from backend if captured]"}
    ```
*   **Backend `jean-memory-service` Logs (Startup OK, but no clear error for the failing request path):**
    *   Logs show Uvicorn startup and router initialization, but specific request logs for `/api/auth/google/url` showing the 400 reason are missing or not detailed enough in what\'s been shared so far.

## 4. Next Steps & Debugging Checklist

The primary goal is to understand *why* the backend is returning a 400 error for the `/api/auth/google/url` request.

### 4.1. Backend Investigation (Priority High)

1.  **Examine Backend Code for `/api/auth/google/url`:**
    *   **File:** Locate the Python file in the backend (`app/routers/google_auth_router.py` or similar) that defines the `/api/auth/google/url` endpoint.
    *   **Check:**
        *   What parameters does this endpoint expect (query, body, headers)?
        *   Is `user_id` expected? Is it validated? How?
        *   What could cause a FastAPI/Pydantic validation error leading to a 400?
        *   What are the exact conditions under which it returns a 400 status?
        *   Does it have sufficient logging to show incoming request details and reasons for failure?
2.  **Add Detailed Logging to the Backend Endpoint:**
    *   Modify the `/api/auth/google/url` endpoint handler in the backend to log:
        *   Received query parameters.
        *   Received headers (especially `Authorization` if it tries to decode it, though it shouldn\'t for this specific URL which is for *getting* the auth URL).
        *   Any exceptions or validation errors in a `try-except` block.
    *   **Example (Python/FastAPI):**
        ```python
        import logging
        logger = logging.getLogger(__name__)

        @router.get("/url")
        async def get_google_auth_url(request: Request, user_id: Optional[str] = None): # Check if user_id is actually used
            logger.info(f"Received request for /api/auth/google/url")
            logger.info(f"Query params: {request.query_params}")
            logger.info(f"Headers: {request.headers}")
            try:
                # ... existing logic ...
                if not all_required_conditions_met: # Replace with actual conditions
                    logger.error("Condition not met for generating Google auth URL")
                    raise HTTPException(status_code=400, detail="Missing required information")
                auth_url = "..." # generate the URL
                return {"auth_url": auth_url}
            except HTTPException as he:
                logger.error(f"HTTPException in get_google_auth_url: {he.detail}")
                raise
            except Exception as e:
                logger.exception("Unexpected error in get_google_auth_url")
                raise HTTPException(status_code=500, detail="Internal server error")
        ```
3.  **Deploy Backend with Enhanced Logging & Retest:**
    *   Build and push the updated backend Docker image.
    *   Deploy the `jean-memory-service` with the new image.
4.  **Analyze Backend Logs After Test:**
    *   Trigger the Google Auth flow from `https://app.jeantechnologies.com/login.html`.
    *   **Command:** `gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=jean-memory-service AND severity>=WARNING" --limit=50 --format=json`
    *   Look for the detailed logs from the `/api/auth/google/url` endpoint. This should reveal the exact reason for the 400.

### 4.2. Frontend Investigation (If Backend Investigation is Inconclusive)

1.  **Ensure Frontend Proxy Logs Backend Error *Body*:**
    *   The current `frontend/server.js` has `JSON.stringify(backendResponse.data, null, 2)` which *should* capture this. Double-check that these logs are appearing in Cloud Logging for the `jean-memory-frontend` service when a 400 occurs.
    *   **Command:** `gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=jean-memory-frontend AND textPayload:ERROR" --limit=20 --format=json`
2.  **Simplify the Proxied Request (Temporarily for testing):**
    *   If the `user_id` parameter is suspect, temporarily modify `frontend/server.js` to *not* send it, or send a hardcoded valid one, to see if the backend response changes. This requires knowing what the backend expects.

### 4.3. Direct Backend Test (Alternative/Confirmation)

1.  **Use `curl` with an ID token to hit the backend endpoint directly:**
    *   This bypasses the frontend proxy and IAP, testing the backend service in isolation with a valid service-to-service token.
    *   **Step 1: Get Service Account ID Token (from your local machine with gcloud and appropriate permissions):**
        ```bash
        TOKEN=$(gcloud auth print-identity-token --audiences=https://jean-memory-service-YOUR_PROJECT_HASH-uc.a.run.app)
        # Replace YOUR_PROJECT_HASH with the actual hash from your backend service URL
        ```
    *   **Step 2: Make the `curl` request:**
        ```bash
        curl -H "Authorization: Bearer $TOKEN" "https://jean-memory-service-YOUR_PROJECT_HASH-uc.a.run.app/api/auth/google/url?user_id=test-debug-user" -v
        ```
        Or without `user_id` if testing that:
        ```bash
        curl -H "Authorization: Bearer $TOKEN" "https://jean-memory-service-YOUR_PROJECT_HASH-uc.a.run.app/api/auth/google/url" -v
        ```
    *   **Analyze:** The output of this `curl` command (especially with `-v` for verbose) will show the exact response from the backend. If this also returns a 400, the issue is definitively within the backend endpoint. If this returns a 200, the issue might be related to how the frontend proxy is constructing or sending the request, or a subtle difference in the token it generates (though unlikely if the audience is correct).

## 5. Build & Deployment Quick Reference

### Backend (`jean-memory-service`):

1.  **Navigate to backend directory:** `cd backend`
2.  **Build Docker Image:**
    ```bash
    docker build --platform linux/amd64 -t us-central1-docker.pkg.dev/gen-lang-client-0888810452/jean-memory-repo/jean-memory-service:latest .
    ```
3.  **Push Docker Image:**
    ```bash
    docker push us-central1-docker.pkg.dev/gen-lang-client-0888810452/jean-memory-repo/jean-memory-service:latest
    ```
4.  **Deploy to Cloud Run:**
    ```bash
    gcloud run deploy jean-memory-service \
        --image=us-central1-docker.pkg.dev/gen-lang-client-0888810452/jean-memory-repo/jean-memory-service:latest \
        --region=us-central1 \
        --no-allow-unauthenticated \
        --service-account=276083385911-compute@developer.gserviceaccount.com \
        --add-cloudsql-instances=gen-lang-client-0888810452:us-central1:jean-memory-db \
        --set-env-vars="DATABASE_URL=postgresql+asyncpg://jean_app_user:YOUR_DB_PASSWORD@/postgres?host=/cloudsql/gen-lang-client-0888810452:us-central1:jean-memory-db,GEMINI_API_KEY=YOUR_GEMINI_KEY,GOOGLE_CLIENT_ID=YOUR_GOOGLE_CLIENT_ID,GOOGLE_CLIENT_SECRET=YOUR_GOOGLE_CLIENT_SECRET,GOOGLE_REDIRECT_URI=https://app.jeantechnologies.com/auth/google/callback.html"
        # Ensure all ENV VARS are correctly set
    ```

### Frontend (`jean-memory-frontend`):

1.  **Navigate to frontend directory:** `cd frontend`
2.  **Build Docker Image:**
    ```bash
    docker build --platform linux/amd64 -t us-central1-docker.pkg.dev/gen-lang-client-0888810452/jean-memory-repo/jean-memory-frontend:latest .
    ```
3.  **Push Docker Image:**
    ```bash
    docker push us-central1-docker.pkg.dev/gen-lang-client-0888810452/jean-memory-repo/jean-memory-frontend:latest
    ```
4.  **Deploy to Cloud Run:**
    ```bash
    gcloud run deploy jean-memory-frontend \
        --image=us-central1-docker.pkg.dev/gen-lang-client-0888810452/jean-memory-repo/jean-memory-frontend:latest \
        --region=us-central1 \
        --no-allow-unauthenticated \
        --service-account=276083385911-compute@developer.gserviceaccount.com \
        --set-env-vars="BACKEND_URL=https://jean-memory-service-YOUR_PROJECT_HASH-uc.a.run.app,NODE_ENV=production"
        # Replace YOUR_PROJECT_HASH
    ```

## 6. Log Checking Quick Reference

*   **Frontend Logs (Proxy activity, client-side interaction simulation):**
    ```bash
    gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=jean-memory-frontend" --limit=50 --format=json --project=gen-lang-client-0888810452
    ```
    Filter for errors:
    ```bash
    gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=jean-memory-frontend AND severity>=ERROR" --limit=50 --format=json --project=gen-lang-client-0888810452
    ```
*   **Backend Logs (API endpoint logic, database interactions, internal errors):**
    ```bash
    gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=jean-memory-service" --limit=50 --format=json --project=gen-lang-client-0888810452
    ```
    Filter for warnings/errors:
    ```bash
    gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=jean-memory-service AND severity>=WARNING" --limit=50 --format=json --project=gen-lang-client-0888810452
    ```

This document should provide a good starting point for the next person. The immediate focus should be on instrumenting and analyzing the backend `/api/auth/google/url` endpoint. 

## 7. Recent Progress (May 11, 2025 Update)

### 7.1 Current Status

We've made progress on the authentication flow but still encounter an issue:

1. **What's Fixed:**
   * All environment variables are now correctly set:
     * `GOOGLE_CLIENT_ID`
     * `GOOGLE_CLIENT_SECRET`
     * `GOOGLE_REDIRECT_URI` (now correctly set to `https://app.jeantechnologies.com/api/auth/google/callback`)
     * `DATABASE_URL`
   * The frontend proxy successfully calls the backend
   * First part of auth flow (generating the auth URL) works correctly

2. **Current Issue:**
   * When Google redirects back to the callback URL, the token exchange still fails with a 400 error
   * The error is from Google's token endpoint, not from our backend
   * Exact error in logs: `Your client has issued a malformed or illegal request.` (Google 400 response)

### 7.2 Token Exchange Endpoint Logs

The frontend successfully makes the callback request to the backend with the Google authorization code:
```
GET /api/auth/google/callback?state=03d1f53c-a6e3-4e7b-9709-bee7af77a568&code=4%2F0AUJR-x4UUD...&scope=email+profile...
```

And the backend attempts to exchange this code with Google, but receives a 400 error.

### 7.3 Probable Causes

1. **PKCE Mismatch:** 
   * The `google_auth_router.py` code uses PKCE (Proof Key for Code Exchange) for enhanced security.
   * If the code verifier generated in `get_oauth_url` does not exactly match what's sent in `handle_oauth_callback`, Google will reject the token exchange request.
   * Token exchange fails if the state or code_verifier values are lost between requests (potential issue with Cloud Run statelessness).

2. **Callback URL Format Mismatch:**
   * The callback URL string must be exactly the same in:
     * Google OAuth console configuration
     * `GOOGLE_REDIRECT_URI` environment variable
     * The token exchange API call to Google
   * Any difference, even trailing slashes, will result in the 400 error.

3. **Multiple Code Usages:**
   * OAuth authorization codes can only be used once.
   * If something in the proxying or flow is resulting in multiple attempts to exchange the same code, subsequent attempts will fail.

### 7.4 Recommended Next Steps

1. **Add Enhanced Logging to Token Exchange:**
   * Add detailed logging in `google_auth_router.py` -> `handle_oauth_callback` function:
   ```python
   # Log exact data being sent to Google token endpoint
   logger.info(f"Token request data being sent to Google: {json.dumps(token_data)}")
   
   # After receiving error response, log detailed information
   try:
     error_response = e.response.json()
     logger.error(f"Google token exchange error details: {json.dumps(error_response)}")
   except:
     logger.error(f"Raw error response: {e.response.text}")
   ```

2. **Dump and Log State Store:**
   * At each step, log the state of the in-memory state store to verify it's persisting correctly:
   ```python
   logger.info(f"Current keys in state_store: {list(self.state_store.keys())}")
   ```

3. **Consider Disabling PKCE Temporarily:**
   * For testing purposes, you can modify the OAuth flow to not use PKCE to see if that resolves the issue.
   * This is for debugging only and should not be used in production.

4. **Compare Approaches:**
   * Look at other NodeJS/Python implementations of Google OAuth to see if there are any best practices we're missing.
   * Check for common pitfalls with Google OAuth in stateless services.

5. **Test Locally First:**
   * Run the backend locally with the exact same settings to test whether the issue is Cloud Run specific.
   * This will help isolate whether the problem is related to the stateless nature of Cloud Run. 