# Backend Application (`app/`)

This directory contains the main FastAPI application configuration and entry points for the JEAN backend.

## Files

-   `app.py`: Defines the FastAPI `app` instance, includes routers, middleware (if any), and defines the primary API endpoints, particularly the `/mcp` endpoint specified in the design document.
-   `main.py`: Contains the application startup logic. This includes initializing necessary services (like the database connection pool) before starting the Uvicorn server. It serves as the main execution script for the backend.
-   Potentially `config.py` or similar for loading and managing application settings (though environment variables are preferred for secrets).

## Responsibilities

-   Initialize and configure the FastAPI application.
-   Define and handle incoming HTTP requests, especially the MCP endpoint.
-   Route requests to the appropriate business logic components (e.g., the `ContextRouter`).
-   Manage application lifecycle events (startup, shutdown).

## Next Steps

1.  Create the basic FastAPI app instance in `app.py`.
2.  Implement the `/mcp` POST endpoint structure in `app.py`, initially perhaps just parsing the request body.
3.  Develop the startup logic in `main.py` to initialize the database (calling `ContextDatabase.initialize()`) and run the Uvicorn server. 