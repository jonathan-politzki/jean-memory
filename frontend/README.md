# JEAN Frontend

This directory will contain the frontend application for JEAN.

## Core Requirements

The frontend should be extremely simple and focused on the following core user flow:

1.  **Sign In:** Allow users to sign in securely using Google Authentication (OAuth).
2.  **Profile Creation (Minimal):** Upon first successful sign-in, create a basic user profile in the backend. This might just be storing the user's Google ID and email.
3.  **Display MCP Configuration:** Immediately display the user-specific Model Context Protocol (MCP) server URL. This URL is the primary artifact the user needs to integrate JEAN with their client application (e.g., Claude Desktop, Cursor).

## Design Philosophy

-   **Minimalism:** Avoid complexity. The *only* goal is user authentication and providing the configuration URL.
-   **Clarity:** Make it obvious what the user needs to do (sign in) and what they need to copy (the URL).
-   **Technology:** To be decided, but prioritize simplicity and speed of development (e.g., static HTML with JavaScript, a lightweight framework like SvelteKit or basic React).

## Next Steps

-   Set up Google OAuth 2.0 credentials.
-   Implement the Google Sign-In button.
-   Create the callback handler to verify the token and communicate with the JEAN backend API to create/retrieve the user profile.
-   Display the MCP URL provided by the backend upon successful login. 