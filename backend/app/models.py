from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List

# --- MCP Request Models ---

class MCPBaseParams(BaseModel):
    user_id: Optional[str] = None # User ID might be implicitly handled by API Key

class MCPStoreParams(MCPBaseParams):
    context_type: str
    content: Dict[str, Any]
    source_identifier: Optional[str] = None

class MCPRetrieveParams(MCPBaseParams):
    query: str
    # Potential future params: context_types: List[str], max_tokens: int

class MCPRequest(BaseModel):
    # Following JSON-RPC style, though not strictly enforced here
    # jsonrpc: str = "2.0"
    # id: int | str
    method: str # e.g., "store", "retrieve"
    params: Dict[str, Any] # We'll parse this into specific models in the endpoint

# --- MCP Response Models ---

class MCPResult(BaseModel):
    type: str
    content: Any
    sources: Optional[List[str]] = None # For comprehensive results

class MCPResponse(BaseModel):
    # jsonrpc: str = "2.0"
    # id: int | str
    result: Optional[MCPResult] = None
    error: Optional[Dict[str, Any]] = None # e.g., {"code": -32600, "message": "Invalid Request"}


# --- Auth Related Models (Example) ---
class UserInfo(BaseModel):
    user_id: int
    api_key: str
    mcp_config_url: str 