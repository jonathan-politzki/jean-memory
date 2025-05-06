# JEAN Autonomous Router System

This document explains the advanced routing system implemented in JEAN that enables AI models to automatically access the most relevant context for a user query without explicit user intervention.

## Overview

The JEAN routing system is designed to intelligently determine which type of context is most relevant to a user's query. This allows for:

1. **Fully autonomous operation** - The model can retrieve relevant context without user instructions
2. **Specialized context processing** - Each type of context is handled by a dedicated router optimized for that domain
3. **Flexibility** - Models can either rely on automatic classification or explicitly specify the context type when they know what they need

## Router Categories

The system includes specialized routers for different domains:

1. **GitHub Router (`github`)** - Code, repositories, pull requests, issues, commits
2. **Notes Router (`notes`)** - Personal notes, knowledge base, documentation, research information
3. **Values Router (`values`)** - Personal values, preferences, principles, decisions
4. **Conversations Router (`conversations`)** - Meeting notes, chat history, discussion summaries
5. **Tasks Router (`tasks`)** - To-do lists, project plans, goals, milestones, deadlines
6. **Work Router (`work`)** - Professional documents, industry knowledge, career information
7. **Media Router (`media`)** - Videos, articles, podcasts, books, content consumption history
8. **Locations Router (`locations`)** - Places visited, travel notes, location-based preferences

## Autonomous Classification

The system uses Google's Gemini AI to classify user queries into the appropriate context type:

1. The query is sent to a Gemini model with instructions to classify it into one of eight categories
2. The classification result is mapped to the corresponding router
3. If Gemini is unavailable, the system falls back to basic keyword matching

## MCP Integration

The system fully integrates with the Model Context Protocol (MCP) to allow AI models to autonomously retrieve context:

### Auto-mode (Fully Autonomous)

```json
{
  "method": "retrieve",
  "params": {
    "query": "What did I write about quantum computing?"
  }
}
```

In this mode, the system automatically:
1. Classifies the query using Gemini
2. Routes to the appropriate specialized router
3. Returns the context to the model

### Explicit-mode (Model-directed)

```json
{
  "method": "retrieve",
  "params": {
    "query": "What did I write about quantum computing?",
    "context_type": "notes"
  }
}
```

In this mode:
1. The model explicitly specifies which router to use
2. The system bypasses classification and directly uses the specified router
3. This is useful when the model knows exactly what type of context it needs

## Implementation Details

- **Context Router** (`context_router.py`) - The main router that determines context type and dispatches to specialized routers
- **Gemini API** (`gemini_api.py`) - Provides classification and context processing services
- **Specialized Routers** - Domain-specific routers that handle different types of context

## Testing

The system can be tested with actual Gemini API using:
```bash
python test_mcp.py
```

Or with a mock implementation (no API key required):
```bash
python test_mcp_mock.py
```

## Future Improvements

1. Implement multi-router retrieval for complex queries that span multiple domains
2. Add confidence scores to Gemini classification to improve routing accuracy
3. Enhance specialized routers with more sophisticated context retrieval mechanisms
4. Implement context caching to improve performance for repeated queries 