# JEAN Memory Frontend

This directory contains the frontend application for the JEAN Memory system. Its primary role is to facilitate user authentication and provide users with the necessary configuration to connect their AI tools (like Claude Desktop or Cursor) to their personal JEAN Memory backend instance.

## Core Purpose and Functionality

The frontend aims to:

1.  **Authenticate Users:** Implement user sign-in, initially focused on Google OAuth. This process verifies the user's identity.
2.  **Provide MCP Configuration:** After successful authentication, the frontend presents the user with their unique Model Context Protocol (MCP) configuration URL and any other necessary details (e.g., API keys if applicable, user ID). This information allows AI clients to securely connect to the user's dedicated memory instance served by the JEAN backend.
3.  **Serve as a User Portal (Potentially):** While initially simple, this frontend could be expanded into a more comprehensive user portal for managing JEAN Memory settings, viewing memory statistics, or initiating specific backend tasks (like syncing a new GitHub repository, as outlined in the main project's `deployment_and_integration_plan.md`).

## Key Components

*   **`server.js`:** An Express.js (Node.js) server. Its main responsibilities are:
    *   Serving static frontend assets (HTML, CSS, client-side JavaScript).
    *   Handling the Google OAuth callback, receiving authentication tokens from Google, and potentially exchanging them for session information or backend tokens.
    *   Serving the user-specific MCP configuration details after authentication.
*   **`public/` directory:** Contains the static assets served to the client's browser.
    *   `index.html`: The landing page, likely containing the "Sign in with Google" button and initiating the OAuth flow.
    *   `profile.html` (or similar): The page displayed after successful login, where the user's MCP configuration is shown.
    *   `css/styles.css`: Stylesheets for the frontend pages.
*   **`package.json`:** Defines the Node.js project dependencies (like Express), and scripts for running, building, or testing the frontend (e.g., `npm run dev`, `npm start`).
*   **`Dockerfile`:** Defines how to build a Docker image for the frontend application, allowing it to be easily containerized and deployed. This typically includes steps to install Node.js, copy project files, install dependencies, and specify the command to start the server.
*   **`kill_port.js`:** A utility script, likely used during development to stop any process that might be occupying the port the frontend server wants to use, ensuring a smooth start-up of the development server.

## User Interaction Flow (Example)

1.  User navigates to the frontend's URL.
2.  User clicks a "Sign in with Google" (or similar) button on `index.html`.
3.  The user is redirected to Google for authentication.
4.  After successful authentication, Google redirects the user back to a callback URL handled by `server.js`.
5.  `server.js` processes the OAuth information, potentially fetches or generates the user's MCP configuration (possibly by communicating with the JEAN backend if needed, using the `BACKEND_URL` environment variable).
6.  The user is then shown a page (`profile.html`) displaying their MCP URL and other relevant connection details.
7.  The user copies this configuration into their AI client (e.g., Claude Desktop, Cursor) to enable JEAN Memory integration.

## Role in the Main JEAN Memory Project

The frontend acts as the primary user-facing entry point for configuring access to the JEAN Memory system. While the backend handles the core memory storage and retrieval, the frontend provides the crucial step of authenticating the user and giving them the "keys" (MCP configuration) to unlock their personal memory store with their preferred AI tools. It bridges the gap between the user and their instance of the backend service.

## Development and Deployment

*   **Local Development:** Typically started with `npm install` (to install dependencies) and then `npm run dev` (or a similar script defined in `package.json`).
*   **Configuration:** Key runtime configurations are managed via environment variables:
    *   `PORT`: The port on which the frontend server listens (e.g., 3000).
    *   `BACKEND_URL`: The URL of the JEAN Memory backend service. The frontend might need to communicate with the backend to validate users or fetch specific configuration details.
    *   Google OAuth Client ID: This needs to be configured (likely in `public/index.html` or as an environment variable passed to `server.js`) to enable Google Sign-In.
*   **Docker Deployment:** The `Dockerfile` allows the frontend to be built as a Docker image (`docker build -t jean-frontend .`) and run as a container (`docker run -p <host_port>:<container_port> -e BACKEND_URL=... jean-frontend`).

## Considerations from `deployment_and_integration_plan.md`

The overall project plan mentions that the frontend will interact with the deployed Cloud Run backend. This frontend would:
*   Make authenticated API calls to the backend.
*   Handle user authentication and pass user identity (`user_id`) to the backend.
*   Potentially include UI for features like initiating a GitHub repo sync by calling backend endpoints (e.g., `POST /integrations/github/sync`). 