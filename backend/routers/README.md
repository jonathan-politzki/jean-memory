# Backend Routers (`routers/`)

This directory houses the core routing logic that determines how context is processed based on user queries.

## Overview

JEAN's unique architecture relies on routing queries to specialized context handlers rather than using generic vector retrieval. This directory implements that logic.

## Files

-   `context_router.py`: Contains the main `ContextRouter` class/functions. Its primary role is to analyze an incoming query (from the MCP `retrieve` method) and determine which specialized router(s) should handle it. It might involve simple keyword matching initially, potentially evolving to use NLP or an LLM call for more sophisticated intent recognition. It also handles combining results if multiple routers are invoked (e.g., for a `comprehensive` context type).
-   `github_router.py`: Implements the `GitHubRouter` class/functions. Responsible for fetching raw GitHub context (from DB cache or GitHub API via a service), formatting it, processing it with its dedicated Gemini API instance, and returning the relevant context.
-   `notes_router.py`: Implements the `NotesRouter` for personal notes.
-   `values_router.py`: Implements the `ValuesRouter` for personal values/preferences.
-   `conversations_router.py`: Implements the `ConversationsRouter` for conversation history.
-   `_base_router.py` (Optional): Could define a base class or interface for specialized routers to ensure consistency.

## Responsibilities

-   **Context Type Determination:** Analyze queries to decide the relevant context domain(s).
-   **Dispatching:** Route requests to the appropriate specialized router implementations.
-   **Specialized Context Handling:** Each specialized router manages fetching, processing (via Gemini), and formatting context for its specific domain.
-   **Result Aggregation:** Combine results from multiple routers when necessary.

## Next Steps

1.  Implement the basic `determine_context_type` function in `context_router.py` (using simple keyword matching as shown in the guide).
2.  Create the `ContextRouter` class structure in `context_router.py`, including the `route` method stub.
3.  Create placeholder classes for each specialized router (`GitHubRouter`, `NotesRouter`, etc.) with method stubs for `get_context` and `get_raw_context`. 