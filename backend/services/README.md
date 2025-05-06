# Backend Services (`services/`)

This directory contains modules that act as clients or wrappers for interacting with external APIs and services.

## Overview

The core logic in the routers often needs to communicate with external systems (like the Gemini API for AI processing or the GitHub API for fetching code). This directory centralizes that communication logic, keeping the routers focused on context handling.

## Files

-   `gemini_api.py`: Contains the `GeminiAPI` class/service. This class is responsible for:
    -   Initializing the `google.generativeai` client with the API key.
    -   Providing a method (`process`) that takes context type, data, and query.
    -   Formatting the context data into a prompt suitable for Gemini, including the appropriate system prompt based on the context type.
    -   Calling the Gemini API (using `asyncio.to_thread` or similar for non-blocking calls).
    -   Handling potential caching of Gemini API calls.
    -   Includes specific formatting functions (`format_github`, `format_notes`, etc.).
-   `github_client.py` (Example): If direct interaction with the GitHub API is needed (e.g., fetching repositories if not cached), a dedicated client class would go here. It would handle authentication (OAuth tokens) and API calls to GitHub.
-   Other potential services: Clients for interacting with Notes APIs (Obsidian, Notion), Twitter API, etc., if those context sources are implemented.

## Responsibilities

-   **Abstraction:** Provide a clean interface for other parts of the backend (like routers) to interact with external services without needing to know the specifics of the API calls or authentication.
-   **API Interaction:** Handle the details of making requests to external APIs (Gemini, GitHub, etc.).
-   **Authentication:** Manage API keys and authentication tokens for external services.
-   **Error Handling:** Implement basic error handling and retry logic for external API calls.
-   **Formatting/Parsing:** Prepare data for sending to APIs and parse the responses.

## Next Steps

1.  Implement the `GeminiAPI` class structure in `gemini_api.py`, including the `__init__` method to configure the API key.
2.  Create the `process` method stub in `GeminiAPI`, taking `context_type`, `context_data`, and `query`.
3.  Implement the prompt formatting logic within `GeminiAPI` based on the examples (including system prompts and context formatting functions like `format_github`).
4.  Integrate the actual `genai.GenerativeModel('gemini-1.5-pro').generate_content` call within the `process` method, ensuring it runs asynchronously. 