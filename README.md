# jean-memory
MCP Personal Memory Service
1. Overview & Vision
This project aims to create a cloud-hosted Personal Memory Service designed to provide long-term, context-aware memory capabilities to AI models and agents via the Model Context Protocol (MCP).

The core vision is to build a simple, reliable, and extensible backend service that:

Receives conversation snippets or explicit data points from MCP clients.
Processes this data implicitly using LLMs to extract key information (summaries, facts, preferences).
Generates vector embeddings for semantic understanding.
Persists this processed memory (text chunks, vectors, facts) securely in a cloud database (Supabase).
Provides relevant memories back to MCP clients upon request, primarily via semantic search.
Ensures strict separation of memory data per user.
Prioritizes ease of setup and deployment using modern cloud infrastructure.
This service acts as an external, persistent "brain" that AI applications can consult, enabling more personalized and contextually grounded interactions over time. We will start with a focus on Vector + Key-Value storage for simplicity and effectiveness.

2. Core Features (Phase 1)
MCP Integration: Expose memory functions as standard MCP tools over an HTTP API.
Implicit Memory Processing: Accept conversation turns (user_id, snippet) via MCP. Use a configurable LLM (e.g., GPT-4o-mini, Claude Haiku) to extract summaries or key facts from the snippet.
Vector Embedding Generation: Generate vector embeddings for processed text chunks using a configurable embedding model (e.g., OpenAI text-embedding-3-small, Sentence Transformers).
Persistent Storage (Supabase):
Store processed text chunks and their vector embeddings using pgvector.
Store extracted key-value facts (e.g., preferences, important details).
Semantic Search Retrieval: Provide an MCP tool (search_memory) that takes a query and returns the top_k most semantically relevant memory chunks for a given user using vector similarity search.
Fact Retrieval: Provide an MCP tool (get_fact) to retrieve specific known facts for a user.
Memory Management: Provide basic MCP tools for deleting specific memories or facts (delete_memory, delete_fact).
User Isolation: All data storage and retrieval operations are strictly partitioned by user_id.
3. Architecture
The service follows a standard cloud API architecture:

+-------------+       +---------------------------+       +----------------------+       +---------------------+
| MCP Client  | ----> | Cloud API Gateway /       | ----> | Processing Logic     | ----> | LLM / Embedding API |
| (e.g., IDE, | HTTP  | Serverless Function       |       | (Python/FastAPI)     |       | (OpenAI, Anthropic) |
| Claude App) | POST  | (Vercel, AWS Lambda, etc.)|       | - Parse MCP Request  |       +---------------------+
+-------------+       +---------------------------+       | - Call LLM/Embedding |
                             |                      | - DB Operations        |
                             |                      +-----------+------------+
                             |                                  |
                             | DB Calls                         | DB Calls
                             v                                  v
                       +---------------------------------------------------+
                       | Supabase (PostgreSQL + pgvector)                  |
                       | +-----------------+   +-------------------------+ |
                       | | memories Table  |   | facts Table             | |
                       | | (Chunks+Vectors)|   | (Key-Value Pairs)       | |
                       | +-----------------+   +-------------------------+ |
                       +---------------------------------------------------+
Data Flow Examples:

Storing Memory (process_turn):

MCP Client sends POST request with process_turn tool call, user_id, and conversation_snippet.
API endpoint receives the request.
Processing Logic sends snippet to LLM API for fact/summary extraction.
Processing Logic sends relevant text chunk(s) to Embedding API.
Processing Logic stores extracted facts in facts table and text chunk + vector in memories table in Supabase, associated with user_id.
API sends success response back to MCP Client.
Retrieving Memory (search_memory):

MCP Client sends POST request with search_memory tool call, user_id, query_text, and top_k.
API endpoint receives the request.
Processing Logic sends query_text to Embedding API to get query vector.
Processing Logic performs vector similarity search on memories table in Supabase (filtering by user_id, comparing query vector to stored vectors).
Processing Logic retrieves top K matching memory chunks.
API formats results and sends them back to MCP Client.
4. Technology Stack
Language: Python 3.10+
Web Framework: FastAPI (for building the MCP-compliant HTTP API)
Database: Supabase
PostgreSQL for relational data (facts table).
pgvector extension (enabled in Supabase) for vector storage and search.
LLM API: Configurable - OpenAI, Anthropic, Cohere (via their Python SDKs). Default: OpenAI.
Embedding Model API: Configurable - OpenAI, Cohere, or potentially local Sentence Transformers (if running with sufficient resources). Default: OpenAI text-embedding-3-small.
Cloud Hosting: Serverless Platform (Recommended: Vercel for ease of deployment from GitHub) or Container Platform (Google Cloud Run, AWS Fargate).
Containerization: Docker (Dockerfile provided for consistent environments).
Dependency Management: pip with requirements.txt.
5. Database Schema (Supabase - PostgreSQL + pgvector)
SQL

-- Enable pgvector extension (Run this once in Supabase SQL Editor)
CREATE EXTENSION IF NOT EXISTS vector;

-- Memories Table: Stores processed text chunks and their embeddings
CREATE TABLE memories (
    memory_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,          -- ID provided by the MCP client to isolate user data
    processed_chunk TEXT NOT NULL,  -- The text chunk that was embedded
    embedding VECTOR(1536) NOT NULL, -- Embedding vector. Dimension matches OpenAI 'text-embedding-3-small'. Adjust if using a different model.
    created_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()) NOT NULL,
    metadata JSONB                     -- Optional: Store source info, timestamps, etc.
);

-- Add index for user_id lookup
CREATE INDEX idx_memories_user_id ON memories (user_id);

-- Add index for vector similarity search using HNSW (adjust parameters as needed)
-- Choose distance metric based on embedding model (Cosine is common for OpenAI)
CREATE INDEX idx_memories_embedding ON memories USING hnsw (embedding vector_cosine_ops);
-- Or using IVFFlat (alternative, might need tuning)
-- CREATE INDEX idx_memories_embedding ON memories USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);


-- Facts Table: Stores extracted key-value pairs
CREATE TABLE facts (
    fact_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    fact_key TEXT NOT NULL,             -- The name/key of the fact (e.g., 'preferred_language', 'project_alpha_status')
    fact_value TEXT NOT NULL,           -- The value of the fact
    created_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()) NOT NULL,
    source_memory_id UUID REFERENCES memories(memory_id) ON DELETE SET NULL, -- Optional link back to the memory chunk it came from
    metadata JSONB                     -- Optional: Confidence score, etc.
);

-- Add indexes for efficient fact lookup
CREATE INDEX idx_facts_user_id ON facts (user_id);
CREATE INDEX idx_facts_user_id_key ON facts (user_id, fact_key); -- For looking up specific facts for a user

-- Ensure a user doesn't have duplicate keys (optional, depends on desired behavior)
-- CREATE UNIQUE INDEX idx_facts_user_id_key_unique ON facts (user_id, fact_key);
(Note: Vector dimension VECTOR(1536) is for OpenAI text-embedding-3-small. Adjust if using a different embedding model.)

6. MCP Interface Definition
The service will expose an HTTP endpoint (e.g., /mcp) that accepts POST requests with a JSON-RPC 2.0 payload.

Core MCP Tools:

process_turn

Description: Processes a snippet of conversation to extract and store implicit memories and facts.
Params:
user_id (str): Unique identifier for the user.
conversation_snippet (str): Text content to process.
Returns: {"success": true} or {"success": false, "error": "message"}
search_memory

Description: Searches stored memories for a user based on semantic similarity to a query.
Params:
user_id (str): User identifier.
query_text (str): The search query.
top_k (int, optional, default=5): Number of results to return.
Returns: list[dict] where each dict represents a memory:
JSON

[
  {
    "memory_id": "uuid-...",
    "processed_chunk": "Text of the memory...",
    "created_at": "iso-timestamp",
    "similarity_score": 0.85, // Optional, if provided by vector search
    "metadata": { ... }
  },
  ...
]
get_fact

Description: Retrieves a specific fact stored for the user.
Params:
user_id (str): User identifier.
fact_key (str): The key of the fact to retrieve.
Returns: dict representing the fact or null if not found:
JSON

{
  "fact_id": "uuid-...",
  "fact_key": "preferred_language",
  "fact_value": "Python",
  "created_at": "iso-timestamp",
  "metadata": { ... }
}
delete_memory

Description: Deletes a specific memory chunk.
Params:
user_id (str): User identifier.
memory_id (str): The UUID of the memory to delete.
Returns: {"success": true} or {"success": false, "error": "message"}
delete_fact

Description: Deletes a specific fact.
Params:
user_id (str): User identifier.
fact_id (str): The UUID of the fact to delete. Alternatively, could delete by fact_key.
Returns: {"success": true} or {"success": false, "error": "message"}
(Note: The exact JSON-RPC request/response structure needs to be implemented according to the MCP specification if strict adherence is required, but a simple JSON API following this structure is often sufficient for custom clients.)

7. Setup & Deployment
Prerequisites:

Python 3.10+
Docker (Recommended)
Supabase Account (Sign up at supabase.com)
LLM API Key (e.g., OpenAI)
Embedding Model API Key (e.g., OpenAI)
Local Development Setup:

Clone Repository: git clone [your-repo-url]
Navigate to Directory: cd [your-repo-name]
Create Supabase Project: Set up a new project on Supabase.
Enable pgvector: In the Supabase dashboard -> Database -> Extensions -> Search for vector and enable it.
Run Schema: Copy the SQL from Section 5 into the Supabase SQL Editor and run it.
Environment Variables:
Copy .env.example to .env.
Fill in your Supabase URL, Supabase Anon Key (or Service Role Key - use Service Role Key for backend operations), LLM API Key, Embedding API Key.
Code snippet

SUPABASE_URL="your-supabase-url"
SUPABASE_SERVICE_KEY="your-supabase-service-role-key" # Keep this secret!
OPENAI_API_KEY="your-openai-key"
# Add other keys if using different LLM/Embedding providers
Install Dependencies: pip install -r requirements.txt
Run FastAPI Server: uvicorn main:app --reload (Requires main.py with FastAPI app instance named app).
Cloud Deployment (Vercel Example):

Push to GitHub/GitLab/Bitbucket.
Create Vercel Project: Connect your Git repository to Vercel.
Configure Build Settings: Vercel should auto-detect Python. Ensure it installs dependencies from requirements.txt.
Configure Environment Variables: Add the same variables from your .env file to the Vercel project settings (securely).
Deploy: Vercel will build and deploy the service. You'll get a public URL (e.g., your-project.vercel.app). Your MCP endpoint would be https://your-project.vercel.app/mcp.
Docker:

A Dockerfile will be provided to build a container image.
This allows deployment to container platforms (Cloud Run, Fargate, etc.) or consistent local running via docker run.
8. Usage (MCP Client Interaction)
An MCP client needs to be configured to point to your deployed service URL (e.g., https://your-project.vercel.app/mcp).

Example interaction using curl (replace placeholders):

Bash

# Store a memory
curl -X POST https://your-project.vercel.app/mcp \
     -H "Content-Type: application/json" \
     -d '{
           "jsonrpc": "2.0",
           "method": "process_turn",
           "params": {
             "user_id": "user-123",
             "conversation_snippet": "User: I really enjoyed learning about vector databases today. AI: Yes, they are powerful tools for semantic search!"
           },
           "id": 1
         }'

# Search memory
curl -X POST https://your-project.vercel.app/mcp \
     -H "Content-Type: application/json" \
     -d '{
           "jsonrpc": "2.0",
           "method": "search_memory",
           "params": {
             "user_id": "user-123",
             "query_text": "What did I learn about today?",
             "top_k": 3
           },
           "id": 2
         }'
9. Future Enhancements
Asynchronous Processing: Move LLM/Embedding calls to background tasks (e.g., using Celery/Redis or FastAPI's BackgroundTasks) for faster API responses.
Graph Capabilities: Integrate basic graph storage (e.g., using Supabase relational tables or adding a dedicated graph DB like Neo4j) to capture relationships between memories/entities.
Advanced Retrieval: Implement re-ranking of search results using LLMs, combine vector search with fact lookups more intelligently.
Time-Based Decay/Summarization: Implement mechanisms for older memories to decay in relevance or be periodically summarized.
Management UI: A simple web interface for users to view, manage, and potentially curate their memories.
More Data Connectors: Add MCP tools or ingestion methods for other data sources (files, web pages, etc.).
Authentication/Authorization: Implement more robust auth beyond just trusting the user_id from the client (e.g., using JWTs passed via MCP headers).
10. Contributing
(Placeholder: Add guidelines if you plan for others to contribute.)
Currently, this is a personal project. Contributions are welcome via Pull Requests after discussing changes in Issues.

11. License
This project is licensed under the MIT License. See the LICENSE file for details.
