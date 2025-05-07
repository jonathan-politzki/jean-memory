"""
Core MCP tools for the JEAN Memory system, focusing on generalized memory access.
"""

import logging
import os # Import os for os.getenv
from typing import Dict, Any, Optional, List
from datetime import datetime
from mcp.server.fastmcp import FastMCP, Context
import json
import google.generativeai as genai # Import genai
import asyncio # Import asyncio
import sys # Import sys for print statements

logger = logging.getLogger(__name__)

# --- Gemini Configuration (similar to value_extraction_tools.py) ---
def setup_gemini_for_core_memory():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.warning("GEMINI_API_KEY not set. access_jean_memory synthesis will be limited.")
        return False
    try:
        genai.configure(api_key=api_key)
        logger.info("Gemini API configured successfully for core memory tools.")
        return True
    except Exception as e:
        logger.error(f"Error configuring Gemini API: {e}")
        return False

gemini_ready_for_core = False # Will be set by initialize_mcp_server in mcp_server.py
# A global variable to hold the model instance can be efficient
# but initialize it carefully, perhaps in a lifespan event or on first use after check.
_gemini_model_instance = None
_gemini_model_lock = asyncio.Lock() # Lock for async-safe model initialization

async def get_gemini_model_async():
    global _gemini_model_instance
    if not gemini_ready_for_core:
        logger.warning("Gemini is not ready, cannot get model instance.")
        return None
    
    if _gemini_model_instance is None:
        async with _gemini_model_lock:
            if _gemini_model_instance is None:
                try:
                    # Use the corrected model name based on diagnostic tool output
                    model_name_to_use = "models/gemini-1.5-pro-latest"
                    print(f"JEAN_MEMORY_DIAGNOSTIC: Attempting to use Gemini model: {model_name_to_use}", file=sys.stderr)
                    sys.stderr.flush() # Ensure it gets written out immediately
                    logger.info(f"Attempting to initialize Gemini model: {model_name_to_use}")
                    _gemini_model_instance = await asyncio.to_thread(genai.GenerativeModel, model_name_to_use)
                    logger.info(f"Gemini model '{model_name_to_use}' instance created asynchronously.")
                except Exception as e:
                    logger.error(f"Failed to create Gemini model instance with {model_name_to_use}: {e}")
                    # Fallback attempt with a slightly different common name if the first fails
                    # This is an example, adjust if needed based on typical fallbacks
                    try:
                        model_name_fallback = "gemini-1.5-pro-latest" # Common alias sometimes used
                        logger.warning(f"Primary model failed. Falling back to trying: {model_name_fallback}")
                        _gemini_model_instance = await asyncio.to_thread(genai.GenerativeModel, model_name_fallback)
                        logger.info(f"Gemini model '{model_name_fallback}' instance created asynchronously as fallback.")
                    except Exception as e2:
                        logger.error(f"Failed to create Gemini model instance with fallback {model_name_fallback}: {e2}")
                        return None
    return _gemini_model_instance

# Helper function to format retrieved context for LLM
def format_retrieved_context_for_llm(retrieved_items: List[Dict[str, Any]]) -> str:
    formatted_str = ""
    if not retrieved_items:
        return "No specific memories found for the given criteria.\n"
    
    for item in retrieved_items:
        formatted_str += f"--- Memory Entry (ID: {item.get('id')}, Type: {item.get('context_type')}, Updated: {item.get('updated_at')}) ---\n"
        if isinstance(item.get('content'), dict):
            formatted_str += json.dumps(item.get('content'), indent=2) + "\n"
        elif item.get('content') is not None:
            formatted_str += str(item.get('content')) + "\n"
        else:
            formatted_str += "[No content]\n"
           
        if item.get('metadata'):
            formatted_str += f"Metadata: {json.dumps(item.get('metadata'))}\n"
    formatted_str += "-----------------------------------------------------\n"
    return formatted_str

def register_core_memory_tools(mcp: FastMCP):
    global gemini_ready_for_core # Allow modification of the global
    gemini_ready_for_core = setup_gemini_for_core_memory()
    if not gemini_ready_for_core:
        logger.warning("Core memory tools registered, but Gemini features will be unavailable.")

    logger.info("Registering core memory tools with MCP server")

    @mcp.tool()
    async def create_jean_memory_entry(
        context_type: str,
        content: Dict[str, Any],
        source_identifier: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        ctx: Context = None
    ) -> Dict[str, Any]:
        """Create a new entry in a specified JEAN Memory context bank.
        
        Args:
            context_type: The designated context bank (e.g., 'explicit_note', 'user_preference', 'project_update').
            content: A dictionary containing the main data for this memory entry.
            source_identifier: An optional unique identifier for the source of this memory (e.g., 'slack_message_123', 'manual_entry_timestamp').
            metadata: An optional dictionary for additional, type-specific metadata (e.g., tags, priority, source_url).
            ctx: MCP context object.
        
        Returns:
            Dictionary with success status and any relevant identifiers.
        """
        logger.debug(f"create_jean_memory_entry called with metadata: {metadata} (type: {type(metadata)})")

        if not ctx or not ctx.request_context.lifespan_context.db:
            logger.error("Database not available in create_jean_memory_entry")
            return {"success": False, "error": "Database not available"}
        
        db = ctx.request_context.lifespan_context.db
        user_id = ctx.request_context.lifespan_context.user_id
        tenant_id = ctx.request_context.lifespan_context.tenant_id
        
        if not user_id:
            logger.error("User ID not provided in create_jean_memory_entry")
            return {"success": False, "error": "User ID not provided"}
        
        if not context_type or not content:
            return {"success": False, "error": "context_type and content are required"}

        # Ensure source_identifier is unique if not provided, to avoid unintended overwrites by ON CONFLICT
        # For truly new entries, a unique source_identifier or None is appropriate.
        # If an update to an existing entry is intended, the caller MUST provide the correct source_identifier.
        effective_source_identifier = source_identifier if source_identifier else f"{context_type}_{datetime.utcnow().isoformat()}_{str(user_id)}"

        # Validate metadata type before passing to DB
        processed_metadata = None
        if metadata is not None:
            if isinstance(metadata, dict):
                processed_metadata = metadata
            else:
                logger.warning(f"Received metadata of unexpected type: {type(metadata)}. Value: {metadata}. Forcing to None.")
                # Optionally, could return an error here if metadata must be a dict when provided
                # return {"success": False, "error": f"Invalid metadata type: {type(metadata)}. Expected dict or None."}
        
        try:
            success = await db.store_context(
                user_id=user_id,
                tenant_id=tenant_id,
                context_type=context_type,
                content=content, # content is already a Dict[str, Any]
                source_identifier=effective_source_identifier,
                metadata=processed_metadata # Use the validated metadata
            )
            
            if success:
                logger.info(f"Successfully stored memory entry. User: {user_id}, Type: {context_type}, Source ID: {effective_source_identifier}")
                return {
                    "success": True,
                    "message": f"Memory entry created/updated in '{context_type}' bank.",
                    "source_identifier": effective_source_identifier
                }
            else:
                logger.error(f"Failed to store memory entry via db.store_context. User: {user_id}, Type: {context_type}")
                return {"success": False, "error": "Failed to store memory entry in database."}
            
        except Exception as e:
            logger.exception(f"Error creating JEAN Memory entry (User: {user_id}, Type: {context_type}): {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    async def access_jean_memory(
        current_query: str,
        task_description: str,
        relevant_topics: Optional[List[str]] = None,
        target_context_types: Optional[List[str]] = None,
        max_retrieved_items_per_type: int = 5,
        ctx: Context = None
    ) -> Dict[str, Any]:
        """Accesses JEAN Memory to retrieve, synthesize, or infer relevant information.
        Use this tool when understanding past interactions, user preferences, stored data,
        or other contextual history would significantly improve your response.
        Clearly state what you hope to understand or retrieve in 'task_description'.
        
        Available context types include:
        - "user_preference": For user likes, dislikes, preferences, and values
        - "explicit_note": For notes, facts, and specific information explicitly shared
        - "user_profile": For personal information like name, occupation, etc.
        - "project_update": For information about ongoing projects
        
        You can specify target_context_types as a list (e.g., ["user_profile", "user_preference"])
        to focus on specific memory categories, otherwise default ones will be used.
        """
        logger.info(f"access_jean_memory called. Query: '{current_query}', Task: '{task_description}', Topics: {relevant_topics}, Target Types: {target_context_types}")

        if not ctx or not ctx.request_context.lifespan_context.db:
            logger.error("Database not available in access_jean_memory")
            return {"success": False, "error": "Database not available"}

        db = ctx.request_context.lifespan_context.db
        user_id = ctx.request_context.lifespan_context.user_id
        tenant_id = ctx.request_context.lifespan_context.tenant_id

        if not user_id:
            logger.error("User ID not provided in access_jean_memory")
            return {"success": False, "error": "User ID not provided"}

        # Determine context types to query
        types_to_query = target_context_types
        if not types_to_query:
            # Default types if not specified by the LLM; include more context types by default
            types_to_query = ["user_preference", "explicit_note", "user_profile"]
            logger.info(f"No target_context_types provided, defaulting to: {types_to_query}")

        all_retrieved_items = []
        search_performed = False

        # Prioritize search if relevant_topics or a meaningful current_query is given
        # For simplicity, we'll use relevant_topics or a part of current_query as search term for now.
        # More advanced query generation can be added.
        search_term = None
        if relevant_topics and relevant_topics[0]: # Use first topic as search term
            search_term = relevant_topics[0]
        elif current_query and len(current_query.split()) <= 10: # Increased word limit for better search term
            search_term = current_query
       
        if search_term:
            logger.info(f"Attempting search with term: '{search_term}'")
            for context_type in types_to_query:
                try:
                    logger.debug(f"Searching context_type '{context_type}' with term '{search_term}' for user {user_id}")
                    items = await db.search_context(
                        user_id=user_id,
                        tenant_id=tenant_id,
                        context_type=context_type,
                        query=search_term,
                        limit=max_retrieved_items_per_type
                    )
                    if items:
                        logger.info(f"Found {len(items)} items in '{context_type}' matching '{search_term}'")
                        all_retrieved_items.extend(items)
                        search_performed = True
                except Exception as e:
                    logger.exception(f"Error searching '{context_type}' with term '{search_term}': {e}")
       
        # If no search was performed or if we want to supplement with recent items regardless
        # (or if no search term could be derived)
        if not search_performed or not search_term: # Or add a flag: always_get_recent = True
            logger.info(f"Search not performed or no search term; fetching recent items for types: {types_to_query}")
            for context_type in types_to_query:
                try:
                    logger.debug(f"Fetching recent context_type '{context_type}' for user {user_id}")
                    items = await db.get_context(
                        user_id=user_id,
                        tenant_id=tenant_id,
                        context_type=context_type,
                        limit=max_retrieved_items_per_type
                    )
                    if items:
                        logger.info(f"Found {len(items)} recent items in '{context_type}'")
                        # Avoid duplicates if search already found them (simple ID check)
                        existing_ids = {item['id'] for item in all_retrieved_items}
                        for item in items:
                            if item['id'] not in existing_ids:
                                all_retrieved_items.append(item)
                except Exception as e:
                    logger.exception(f"Error fetching recent items for '{context_type}': {e}")

        if not all_retrieved_items:
            logger.info("No items found by search or recent retrieval.")
            return {"success": True, "summary": "No specific memories found matching the criteria.", "raw_context": ""}

        # Format the raw retrieved data for an LLM
        raw_context_str = format_retrieved_context_for_llm(all_retrieved_items)
       
        # --- Gemini Synthesis Step ---
        if not gemini_ready_for_core:
            logger.warning("Gemini not configured, returning raw context from access_jean_memory.")
            return {
                "success": True, 
                "summary": "I found some memory items, but cannot synthesize them properly. Here's what I found:",
                "retrieved_raw_context_for_llm": raw_context_str,
                "debug_retrieved_item_count": len(all_retrieved_items)
            }
        
        gemini_model = await get_gemini_model_async() # Use the new async getter
        if not gemini_model:
            logger.error("Failed to get Gemini model instance, returning raw context.")
            return {
                "success": True, 
                "summary": "I found some memory items, but could not process them properly. Here's what I found:",
                "retrieved_raw_context_for_llm": raw_context_str,
                "debug_retrieved_item_count": len(all_retrieved_items)
            }

        # Craft the prompt for Gemini
        gemini_prompt = f"""
        You are an AI assistant helping to understand a user based on their stored memories and a current task.
        Current user query to the main AI: "{current_query}"
        The main AI wants to achieve the following by consulting the user's memory: "{task_description}"
        
        Below is a collection of potentially relevant memory entries retrieved for this user. 
        Each entry has a type (e.g., user_preference, explicit_note), content, and metadata.
        
        Your goal is to synthesize this information to provide a concise understanding, insight, or answer 
        that directly helps the main AI with its task_description related to the current_query.
        Focus on extracting what is most pertinent.

        IMPORTANT INSTRUCTIONS:
        1. If the 'Retrieved Memories' section is empty or contains no information directly relevant to the 'task_description' and 'current_query', explicitly state that no relevant memories were found or that the found memories do not directly address the task. Do NOT invent information or over-interpret unrelated memories.
        2. If some memories are found but are only tangentially relevant, you can mention them briefly but clearly indicate their limited relevance to the specific task.
        3. Your synthesized understanding should be truthful to the provided memories.
        
        Retrieved Memories:
        {raw_context_str}
        
        Synthesized Understanding (provide a direct, helpful summary or answer for the main AI, adhering to the IMPORTANT INSTRUCTIONS above):
        """
        
        logger.debug(f"Sending prompt to Gemini for synthesis. Length: {len(gemini_prompt)}")
        
        try:
            # Use asyncio.to_thread for the synchronous generate_content call
            response = await asyncio.to_thread(gemini_model.generate_content, gemini_prompt)
            synthesized_text = response.text
            logger.info("Successfully received synthesized understanding from Gemini.")
            return {
                "success": True,
                "summary": synthesized_text,
                "debug_retrieved_item_count": len(all_retrieved_items),
                "debug_gemini_prompt_length": len(gemini_prompt)
            }
        except Exception as e:
            logger.exception(f"Error during Gemini API call in access_jean_memory: {e}")
            # Improved error message and better fallback behavior
            error_msg = f"Gemini synthesis failed: {str(e)}"
            return {
                "success": False, 
                "error": error_msg,
                "summary": "Gemini synthesis failed. Returning raw context instead.",
                "retrieved_raw_context_for_llm": raw_context_str, 
                "debug_retrieved_item_count": len(all_retrieved_items)
            }
        # --- End Gemini Synthesis Step ---

    @mcp.tool(name="diagnose_list_gemini_models") # Explicit name for clarity
    async def list_available_gemini_models(ctx: Context = None) -> Dict[str, Any]:
        """Lists available Gemini models to help diagnose connection/model name issues.
           This is a diagnostic tool.
        Args:
            ctx: MCP context object (not directly used for model listing, but good practice).
        Returns:
            Dictionary with a list of model names or an error.
        """
        if not gemini_ready_for_core:
            return {"success": False, "error": "Gemini API not configured (GEMINI_API_KEY likely missing)."}
        
        try:
            logger.info("Attempting to list available Gemini models...")
            # The listing of models is typically synchronous
            models_list = await asyncio.to_thread(lambda: [m.name for m in genai.list_models() if "generateContent" in m.supported_generation_methods])
            logger.info(f"Available Gemini models supporting generateContent: {models_list}")
            return {
                "success": True,
                "available_models_for_generateContent": models_list
            }
        except Exception as e:
            logger.exception(f"Error listing Gemini models: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool(name="clear_jean_memory_bank")
    async def clear_jean_memory_bank(
        context_type_to_clear: str,
        ctx: Context = None
    ) -> Dict[str, Any]:
        """Clears all memory entries for the current user from a specified context bank.
        Useful for testing or resetting specific types of memories.

        Args:
            context_type_to_clear: The name of the context bank to clear (e.g., 'user_preference', 'explicit_note').
            ctx: MCP context object.
        
        Returns:
            Dictionary with success status.
        """
        if not ctx or not ctx.request_context.lifespan_context.db:
            logger.error("Database not available in clear_jean_memory_bank")
            return {"success": False, "error": "Database not available"}
        
        db = ctx.request_context.lifespan_context.db
        user_id = ctx.request_context.lifespan_context.user_id
        tenant_id = ctx.request_context.lifespan_context.tenant_id
        
        if not user_id:
            logger.error("User ID not provided in clear_jean_memory_bank")
            return {"success": False, "error": "User ID not provided"}
        
        if not context_type_to_clear:
            return {"success": False, "error": "context_type_to_clear is required"}

        try:
            success = await db.delete_context_by_type_and_user(
                user_id=user_id,
                tenant_id=tenant_id,
                context_type=context_type_to_clear
            )
            
            if success:
                logger.info(f"Successfully cleared context bank '{context_type_to_clear}' for user {user_id}.")
                return {
                    "success": True,
                    "message": f"All entries in context bank '{context_type_to_clear}' have been cleared for the current user."
                }
            else:
                logger.error(f"Failed to clear context bank '{context_type_to_clear}' for user {user_id} via db method.")
                return {"success": False, "error": f"Database operation failed to clear context bank '{context_type_to_clear}'."}
            
        except Exception as e:
            logger.exception(f"Error clearing context bank '{context_type_to_clear}' for user {user_id}: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    async def create_user_profile(
        name: Optional[str] = None,
        details: Dict[str, Any] = None,
        ctx: Context = None
    ) -> Dict[str, Any]:
        """Create or update a user's profile information in memory.
        
        This is a specialized wrapper around create_jean_memory_entry specifically for user profile data.
        
        Args:
            name: The user's name (optional)
            details: Additional user details like occupation, location, etc. (optional)
            ctx: MCP context object.
        
        Returns:
            Dictionary with success status and relevant information.
        """
        logger.info(f"Creating/updating user profile with name: {name}, details: {details}")
        
        if not ctx or not ctx.request_context.lifespan_context.db:
            logger.error("Database not available in create_user_profile")
            return {"success": False, "error": "Database not available"}
        
        # Create a content dictionary with all provided information
        content = {}
        if name:
            content["name"] = name
        
        if details and isinstance(details, dict):
            # Add all the details to the content
            content.update(details)
        
        if not content:
            return {"success": False, "error": "No profile information provided. Please provide name or details."}
        
        # Use the standard memory creation function with user_profile context type
        # Using a consistent source identifier makes it update existing entries
        source_id = f"user_profile_{ctx.request_context.lifespan_context.user_id}"
        metadata = {"tags": ["profile", "personal_info"]}
        
        try:
            # Call the existing create_jean_memory_entry function
            result = await create_jean_memory_entry(
                context_type="user_profile",
                content=content,
                source_identifier=source_id,
                metadata=metadata,
                ctx=ctx
            )
            
            if result.get("success"):
                return {
                    "success": True,
                    "message": "User profile information saved successfully.",
                    "profile_data": content
                }
            else:
                return result  # Pass through any error from create_jean_memory_entry
                
        except Exception as e:
            logger.exception(f"Error in create_user_profile: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    async def advanced_memory_access(
        query: str,
        context_types: List[str],
        max_items_per_type: int = 5,
        ctx: Context = None
    ) -> Dict[str, Any]:
        """Advanced memory access that queries multiple context types with better prioritization.
        
        This tool allows you to search across multiple memory banks at once and get combined results.
        
        Args:
            query: What you're looking for (e.g., "user's name" or "favorite color")
            context_types: List of context types to search, in priority order (e.g., ["user_profile", "user_preference"])
            max_items_per_type: Maximum items to retrieve per context type
            ctx: MCP context object
            
        Returns:
            Dictionary with comprehensive results across all specified context types
        """
        logger.info(f"Advanced memory access called with query: '{query}', types: {context_types}")
        
        if not ctx or not ctx.request_context.lifespan_context.db:
            logger.error("Database not available in advanced_memory_access")
            return {"success": False, "error": "Database not available"}

        db = ctx.request_context.lifespan_context.db
        user_id = ctx.request_context.lifespan_context.user_id
        tenant_id = ctx.request_context.lifespan_context.tenant_id
        
        if not user_id:
            logger.error("User ID not provided in advanced_memory_access")
            return {"success": False, "error": "User ID not provided"}
            
        if not context_types:
            logger.warning("No context types provided, using defaults")
            context_types = ["user_profile", "user_preference", "explicit_note"]
            
        # Results organized by context type
        results_by_type = {}
        combined_items = []
        
        # First, try to search for exact matches in each context type
        for context_type in context_types:
            try:
                items = await db.search_context(
                    user_id=user_id,
                    tenant_id=tenant_id,
                    context_type=context_type,
                    query=query,
                    limit=max_items_per_type
                )
                
                if items:
                    logger.info(f"Found {len(items)} items in '{context_type}' matching '{query}'")
                    results_by_type[context_type] = items
                    combined_items.extend(items)
                else:
                    # If search found nothing, get recent items as fallback
                    logger.info(f"No search results for '{context_type}', getting recent items")
                    recent_items = await db.get_context(
                        user_id=user_id,
                        tenant_id=tenant_id,
                        context_type=context_type,
                        limit=max_items_per_type
                    )
                    
                    if recent_items:
                        logger.info(f"Found {len(recent_items)} recent items in '{context_type}'")
                        results_by_type[context_type] = recent_items
                        combined_items.extend(recent_items)
                    else:
                        results_by_type[context_type] = []
                        
            except Exception as e:
                logger.exception(f"Error accessing memory type '{context_type}': {e}")
                results_by_type[context_type] = []
                
        if not combined_items:
            return {
                "success": True,
                "summary": "No memory items found across any of the specified context types.",
                "results_by_type": results_by_type
            }
            
        # Format results for consumption
        raw_context = format_retrieved_context_for_llm(combined_items)
        
        # Use Gemini for synthesis if available
        if gemini_ready_for_core:
            gemini_model = await get_gemini_model_async()
            if gemini_model:
                gemini_prompt = f"""
                You are an AI assistant helping access a user's memory based on a specific query.
                
                Query: "{query}"
                
                Below are memory entries retrieved from different context types:
                {raw_context}
                
                Please synthesize the most relevant information from these memories that directly answers
                the query. Focus on extracting the most accurate and specific answer.
                If no information directly answers the query, state that clearly.
                
                Synthesized answer:
                """
                
                try:
                    response = await asyncio.to_thread(gemini_model.generate_content, gemini_prompt)
                    synthesized_text = response.text
                    return {
                        "success": True,
                        "summary": synthesized_text,
                        "results_by_type": results_by_type,
                        "raw_context": raw_context
                    }
                except Exception as e:
                    logger.exception(f"Gemini synthesis failed in advanced_memory_access: {e}")
                    # Fall through to non-Gemini response
            
        # If Gemini not available or failed, return structured data
        return {
            "success": True,
            "summary": "Retrieved memory items across multiple context types.",
            "results_by_type": results_by_type,
            "raw_context": raw_context
        } 