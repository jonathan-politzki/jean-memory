"""
Core MCP tools for the JEAN Memory system, focusing on generalized memory access.
"""

import logging
import os
from typing import Dict, Any, Optional, List
from datetime import datetime
from mcp.server.fastmcp import FastMCP, Context
import json
import google.generativeai as genai
import asyncio
import sys

logger = logging.getLogger(__name__)

# --- Gemini Configuration for memory synthesis ---
def setup_gemini_for_core_memory():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.warning("GEMINI_API_KEY not set. Memory synthesis will be limited.")
        return False
    try:
        genai.configure(api_key=api_key)
        logger.info("Gemini API configured successfully for memory tools.")
        return True
    except Exception as e:
        logger.error(f"Error configuring Gemini API: {e}")
        return False

gemini_ready_for_core = False  # Will be set during initialization
_gemini_model_instance = None
_gemini_model_lock = asyncio.Lock()  # Lock for async-safe model initialization

async def get_gemini_model_async():
    global _gemini_model_instance
    if not gemini_ready_for_core:
        logger.warning("Gemini is not ready, cannot get model instance.")
        return None
    
    if _gemini_model_instance is None:
        async with _gemini_model_lock:
            if _gemini_model_instance is None:
                try:
                    model_name_to_use = "models/gemini-1.5-pro-latest"
                    logger.info(f"Attempting to initialize Gemini model: {model_name_to_use}")
                    _gemini_model_instance = await asyncio.to_thread(genai.GenerativeModel, model_name_to_use)
                    logger.info(f"Gemini model '{model_name_to_use}' instance created successfully.")
                except Exception as e:
                    logger.error(f"Failed to create Gemini model instance with {model_name_to_use}: {e}")
                    try:
                        model_name_fallback = "gemini-1.5-pro-latest"
                        logger.warning(f"Primary model failed. Falling back to trying: {model_name_fallback}")
                        _gemini_model_instance = await asyncio.to_thread(genai.GenerativeModel, model_name_fallback)
                        logger.info(f"Gemini model '{model_name_fallback}' instance created as fallback.")
                    except Exception as e2:
                        logger.error(f"Failed to create Gemini model with fallback {model_name_fallback}: {e2}")
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

# Internal helper function to store context
async def _store_context(
    context_type: str,
    content: Dict[str, Any],
    source_identifier: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    ctx: Context = None
) -> Dict[str, Any]:
    """Internal function to store context in the database."""
    if not ctx or not ctx.request_context.lifespan_context.db:
        logger.error("Database not available in _store_context")
        return {"success": False, "error": "Database not available"}
    
    db = ctx.request_context.lifespan_context.db
    user_id = ctx.request_context.lifespan_context.user_id
    tenant_id = ctx.request_context.lifespan_context.tenant_id
    
    if not user_id:
        logger.error("User ID not provided in _store_context")
        return {"success": False, "error": "User ID not provided"}
    
    if not context_type or not content:
        return {"success": False, "error": "context_type and content are required"}

    # Generate a source_identifier if none provided
    effective_source_identifier = source_identifier if source_identifier else f"{context_type}_{datetime.utcnow().isoformat()}_{str(user_id)}"

    # Validate metadata
    processed_metadata = None
    if metadata is not None:
        if isinstance(metadata, dict):
            processed_metadata = metadata
        else:
            logger.warning(f"Received metadata of unexpected type: {type(metadata)}. Value: {metadata}. Forcing to None.")
    
    try:
        success = await db.store_context(
            user_id=user_id,
            tenant_id=tenant_id,
            context_type=context_type,
            content=content,
            source_identifier=effective_source_identifier,
            metadata=processed_metadata
        )
        
        if success:
            logger.info(f"Successfully stored context. User: {user_id}, Type: {context_type}, Source ID: {effective_source_identifier}")
            return {
                "success": True,
                "message": f"Memory entry created/updated in '{context_type}' bank.",
                "source_identifier": effective_source_identifier
            }
        else:
            logger.error(f"Failed to store context. User: {user_id}, Type: {context_type}")
            return {"success": False, "error": "Failed to store memory entry in database."}
        
    except Exception as e:
        logger.exception(f"Error storing context (User: {user_id}, Type: {context_type}): {e}")
        return {"success": False, "error": str(e)}

def register_simplified_memory_tools(mcp: FastMCP):
    """Register only the simplified memory tools - the older tools are deprecated."""
    global gemini_ready_for_core
    gemini_ready_for_core = setup_gemini_for_core_memory()
    if not gemini_ready_for_core:
        logger.warning("Memory tools registered, but Gemini synthesis features will be unavailable.")

    logger.info("Registering simplified memory tools with MCP server")

    @mcp.tool()
    async def get_user_memory(
        query: str,
        context_banks: Optional[List[str]] = None,
        ctx: Context = None
    ) -> Dict[str, Any]:
        """Retrieve factual information about the user's life, preferences, and history.
        
        This tool helps recall concrete details like appointments, personal info,
        saved facts, or preferences the user has shared in the past.
        
        Args:
            query: What you're looking for (e.g., "user's name", "upcoming meetings")
            context_banks: Optional specific banks to search, will auto-select appropriate ones if omitted
            ctx: MCP context object
            
        Returns:
            Dictionary with synthesized memory information and relevant context
        """
        logger.info(f"get_user_memory called with query: '{query}', banks: {context_banks}")
        
        if not ctx or not ctx.request_context.lifespan_context.db:
            logger.error("Database not available in get_user_memory")
            return {"success": False, "error": "Database not available"}

        db = ctx.request_context.lifespan_context.db
        user_id = ctx.request_context.lifespan_context.user_id
        tenant_id = ctx.request_context.lifespan_context.tenant_id
        
        if not user_id:
            logger.error("User ID not provided in get_user_memory")
            return {"success": False, "error": "User ID not provided"}
            
        # Auto-select appropriate context banks for factual memory if none specified
        if not context_banks:
            # These are context banks that typically contain factual information
            context_banks = ["user_profile", "explicit_note", "facts", "appointments"]
            logger.info(f"Auto-selected factual memory banks: {context_banks}")
            
        # Results organized by context bank
        results_by_type = {}
        combined_items = []
        
        # First, try to search for exact matches in each context bank
        for context_type in context_banks:
            try:
                items = await db.search_context(
                    user_id=user_id,
                    tenant_id=tenant_id,
                    context_type=context_type,
                    query=query,
                    limit=5  # Reasonable limit for each bank
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
                        limit=3  # Fewer items for fallback
                    )
                    
                    if recent_items:
                        logger.info(f"Found {len(recent_items)} recent items in '{context_type}'")
                        results_by_type[context_type] = recent_items
                        combined_items.extend(recent_items)
                    else:
                        results_by_type[context_type] = []
                        
            except Exception as e:
                logger.exception(f"Error accessing memory bank '{context_type}': {e}")
                results_by_type[context_type] = []
                
        if not combined_items:
            return {
                "success": True,
                "summary": f"NO_RELEVANT_MEMORY_FOUND: No stored memories about '{query}'",
                "details": "I don't have any stored information about this topic.",
                "action_needed": "Ask the user directly for this information and store it with store_memory"
            }
            
        # Format results for consumption
        raw_context = format_retrieved_context_for_llm(combined_items)
        
        # Use Gemini for synthesis if available
        if gemini_ready_for_core:
            gemini_model = await get_gemini_model_async()
            if gemini_model:
                gemini_prompt = f"""
                You are helping retrieve factual information from a user's memory system.
                
                Query: "{query}"
                
                Below are memory entries retrieved from different context banks:
                {raw_context}
                
                Please synthesize the most relevant FACTUAL information that directly answers
                the query. Focus on concrete details, facts, and specific information.
                
                IMPORTANT RESPONSE GUIDELINES:
                1. If NO information directly answers the query, respond with ONLY: "NO_RELEVANT_MEMORY_FOUND: [brief explanation why]"
                2. If the information is sparse or only partially answers the query, begin with: "LIMITED_MEMORY_FOUND: [synthesized information]"
                3. If comprehensive information is found, provide a clear, direct synthesis.
                4. Be extremely precise and only include facts explicitly stated in the memories.
                5. Never invent or assume information not present in the memories.
                
                Synthesized response:
                """
                
                try:
                    response = await asyncio.to_thread(gemini_model.generate_content, gemini_prompt)
                    synthesized_text = response.text
                    return {
                        "success": True,
                        "summary": synthesized_text,
                        "details": raw_context
                    }
                except Exception as e:
                    logger.exception(f"Gemini synthesis failed in get_user_memory: {e}")
                    # Fall through to non-Gemini response
            
        # If Gemini not available or failed, provide structured data with a simple summary
        return {
            "success": True,
            "summary": f"Found {len(combined_items)} memories related to: {query}",
            "details": raw_context,
            "gemini_status": "UNAVAILABLE",
            "note_to_claude": "Gemini synthesis failed. You should analyze the raw memory entries in 'details' yourself and extract the most relevant information for the query. Look for patterns and facts that directly address the query."
        }

    @mcp.tool()
    async def get_user_understanding(
        query: str,
        context_banks: Optional[List[str]] = None,
        ctx: Context = None
    ) -> Dict[str, Any]:
        """Access insights about the user's personality, values, and emotional patterns.
        
        This tool helps understand deeper aspects of the user like their values,
        communication style, decision-making patterns, or emotional preferences.
        
        Args:
            query: What you want to understand (e.g., "how user makes decisions", "user's values")
            context_banks: Optional specific banks to search, will auto-select appropriate ones if omitted
            ctx: MCP context object
            
        Returns:
            Dictionary with synthesized understanding and relevant context
        """
        logger.info(f"get_user_understanding called with query: '{query}', banks: {context_banks}")
        
        if not ctx or not ctx.request_context.lifespan_context.db:
            logger.error("Database not available in get_user_understanding")
            return {"success": False, "error": "Database not available"}

        db = ctx.request_context.lifespan_context.db
        user_id = ctx.request_context.lifespan_context.user_id
        tenant_id = ctx.request_context.lifespan_context.tenant_id
        
        if not user_id:
            logger.error("User ID not provided in get_user_understanding")
            return {"success": False, "error": "User ID not provided"}
            
        # Auto-select appropriate context banks for understanding if none specified
        if not context_banks:
            # These are context banks that typically contain personality/values information
            context_banks = ["user_preference", "values", "personality", "behavior_patterns"]
            logger.info(f"Auto-selected understanding banks: {context_banks}")
            
        # Results organized by context bank
        results_by_type = {}
        combined_items = []
        
        # Search across multiple context banks
        for context_type in context_banks:
            try:
                # For understanding, we want to be more inclusive in our search
                # so we use a broader search approach
                items = await db.search_context(
                    user_id=user_id,
                    tenant_id=tenant_id,
                    context_type=context_type,
                    query=query,
                    limit=7  # More items for understanding context
                )
                
                if items:
                    logger.info(f"Found {len(items)} items in '{context_type}' matching '{query}'")
                    results_by_type[context_type] = items
                    combined_items.extend(items)
                else:
                    # Get recent items as they might contain relevant patterns
                    logger.info(f"No search results for '{context_type}', getting recent items")
                    recent_items = await db.get_context(
                        user_id=user_id,
                        tenant_id=tenant_id,
                        context_type=context_type,
                        limit=5  # More items for pattern recognition
                    )
                    
                    if recent_items:
                        logger.info(f"Found {len(recent_items)} recent items in '{context_type}'")
                        results_by_type[context_type] = recent_items
                        combined_items.extend(recent_items)
                    else:
                        results_by_type[context_type] = []
                        
            except Exception as e:
                logger.exception(f"Error accessing memory bank '{context_type}': {e}")
                results_by_type[context_type] = []
                
        if not combined_items:
            return {
                "success": True,
                "summary": f"NO_RELEVANT_MEMORY_FOUND: No stored memories about '{query}'",
                "details": "I don't have any stored information about this topic.",
                "action_needed": "Ask the user directly for this information and store it with store_memory"
            }
            
        # Format results for consumption
        raw_context = format_retrieved_context_for_llm(combined_items)
        
        # Use Gemini for synthesis if available, with specialized understanding prompt
        if gemini_ready_for_core:
            gemini_model = await get_gemini_model_async()
            if gemini_model:
                gemini_prompt = f"""
                You are helping understand a user's personality, values, and patterns based on their memory.
                
                Query: "{query}"
                
                Below are memory entries that might reveal patterns about this user:
                {raw_context}
                
                Please synthesize a thoughtful understanding that answers the query.
                Focus on identifying patterns, values, preferences, and insights about the user's:
                - Communication style
                - Decision-making approach
                - Values and what matters to them
                - Emotional patterns and preferences
                
                IMPORTANT RESPONSE GUIDELINES:
                1. If NO relevant patterns can be identified, respond with ONLY: "NO_UNDERSTANDING_FOUND: [brief explanation why]"
                2. If the information is sparse or only shows weak patterns, begin with: "LIMITED_UNDERSTANDING_FOUND: [synthesized insights]" 
                3. If clear patterns emerge, provide a nuanced, thoughtful synthesis.
                4. Only make claims that are reasonably supported by evidence in the memories.
                5. Acknowledge uncertainty when appropriate rather than making definitive claims with limited evidence.
                
                Synthesized understanding:
                """
                
                try:
                    response = await asyncio.to_thread(gemini_model.generate_content, gemini_prompt)
                    synthesized_text = response.text
                    return {
                        "success": True,
                        "summary": synthesized_text,
                        "details": raw_context
                    }
                except Exception as e:
                    logger.exception(f"Gemini synthesis failed in get_user_understanding: {e}")
                    # Fall through to non-Gemini response
            
        # If Gemini not available or failed, provide structured data
        return {
            "success": True,
            "summary": f"Found {len(combined_items)} insights related to: {query}",
            "details": raw_context,
            "gemini_status": "UNAVAILABLE",
            "note_to_claude": "Gemini synthesis failed. You should analyze the raw memory entries in 'details' yourself and look for patterns in the user's preferences, values, and behaviors that relate to the query. Focus on understanding personality traits and behavioral patterns."
        }

    @mcp.tool()
    async def store_memory(
        information: Dict[str, Any],
        memory_type: str,
        tags: Optional[List[str]] = None,
        ctx: Context = None
    ) -> Dict[str, Any]:
        """Store information in the user's memory system.
        
        This simplified tool lets you save any type of information to the appropriate memory bank.
        
        Args:
            information: The information to store (a dictionary with relevant fields)
            memory_type: The type of memory to store (e.g., "fact", "preference", "profile", "appointment")
            tags: Optional list of tags to help categorize this memory
            ctx: MCP context object
            
        Returns:
            Dictionary with success status and confirmation
        """
        logger.info(f"store_memory called with type: {memory_type}, information: {information}")
        
        if not ctx or not ctx.request_context.lifespan_context.db:
            logger.error("Database not available in store_memory")
            return {"success": False, "error": "Database not available"}
        
        # Map simple memory_type to actual context bank name
        context_type_mapping = {
            "fact": "explicit_note",
            "profile": "user_profile", 
            "preference": "user_preference",
            "value": "values",
            "appointment": "appointments"
        }
        
        # Use the mapping or the direct value if it's not in the mapping
        context_type = context_type_mapping.get(memory_type.lower(), memory_type)
        
        # Create metadata if tags were provided
        metadata = {"tags": tags} if tags else None
        
        try:
            # Use the internal _store_context function
            result = await _store_context(
                context_type=context_type,
                content=information,
                metadata=metadata,
                ctx=ctx
            )
            
            if result.get("success"):
                return {
                    "success": True,
                    "message": f"Successfully stored information as {memory_type}.",
                    "details": information
                }
            else:
                return result  # Pass through any error
                
        except Exception as e:
            logger.exception(f"Error in store_memory: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    async def delete_memory_entry(
        memory_id: int,
        ctx: Context = None
    ) -> Dict[str, Any]:
        """Delete a specific memory entry by its ID.
        
        This tool allows precise removal of individual memory entries instead of clearing entire banks.
        
        Args:
            memory_id: The ID of the specific memory entry to delete
            ctx: MCP context object
            
        Returns:
            Dictionary with success status
        """
        logger.info(f"delete_memory_entry called for memory ID: {memory_id}")
        
        if not ctx or not ctx.request_context.lifespan_context.db:
            logger.error("Database not available in delete_memory_entry")
            return {"success": False, "error": "Database not available"}
        
        db = ctx.request_context.lifespan_context.db
        user_id = ctx.request_context.lifespan_context.user_id
        tenant_id = ctx.request_context.lifespan_context.tenant_id
        
        if not user_id:
            logger.error("User ID not provided in delete_memory_entry")
            return {"success": False, "error": "User ID not provided"}
        
        try:
            # First verify the entry exists and belongs to this user
            entry = await db.get_context_by_id(
                user_id=user_id,
                tenant_id=tenant_id,
                context_id=memory_id
            )
            
            if not entry:
                logger.warning(f"Memory entry {memory_id} not found or does not belong to user {user_id}")
                return {
                    "success": False, 
                    "message": f"Memory entry with ID {memory_id} not found or you don't have permission to delete it."
                }
            
            # Now delete the entry
            success = await db.delete_context_by_id(
                user_id=user_id,
                tenant_id=tenant_id,
                context_id=memory_id
            )
            
            if success:
                logger.info(f"Successfully deleted memory entry {memory_id} for user {user_id}.")
                return {
                    "success": True,
                    "message": f"Memory entry with ID {memory_id} has been deleted."
                }
            else:
                logger.error(f"Failed to delete memory entry {memory_id} for user {user_id}.")
                return {"success": False, "error": f"Database operation failed to delete memory entry {memory_id}."}
            
        except Exception as e:
            logger.exception(f"Error deleting memory entry {memory_id}: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool(name="initialize_user_memory")
    async def initialize_user_memory(ctx: Context = None) -> Dict[str, Any]:
        """Automatically called at the beginning of each conversation to load user memory.
        
        This tool is automatically invoked when a conversation starts and fetches
        basic information about the user to provide context for the conversation.
        
        Args:
            ctx: MCP context object
            
        Returns:
            Dictionary with user information and memory summary
        """
        logger.info("Automatically initializing user memory at conversation start")
        
        if not ctx or not ctx.request_context.lifespan_context.db:
            logger.error("Database not available in initialize_user_memory")
            return {
                "success": False, 
                "error": "Database not available",
                "note_to_claude": "Memory initialization failed. Please use get_user_memory manually to retrieve user information."
            }
        
        # Gather user information from various memory banks
        try:
            # Get identity information (name, contact details, etc.)
            identity_info = await get_user_memory(
                query="user identity name contact information", 
                context_banks=["user_profile"],
                ctx=ctx
            )
            
            # Get preference information
            preference_info = await get_user_memory(
                query="user preferences and important facts", 
                context_banks=["user_preference", "explicit_note"],
                ctx=ctx
            )
            
            # Get personality insights if available
            personality_info = await get_user_understanding(
                query="user personality, communication style, and values", 
                ctx=ctx
            )
            
            # Combine all information for Claude
            return {
                "success": True,
                "conversation_started": True,
                "memory_initialized": True,
                "user_identity": identity_info.get("summary", "No identity information found"),
                "user_preferences": preference_info.get("summary", "No preference information found"),
                "user_personality": personality_info.get("summary", "No personality insights available"),
                "note_to_claude": "IMPORTANT: This information was automatically loaded at the start of the conversation. Use it to personalize your responses. If specific information is missing, use get_user_memory or get_user_understanding to look it up. Remember to IMMEDIATELY store any new user information you learn using store_memory."
            }
        except Exception as e:
            logger.exception(f"Error in initialize_user_memory: {e}")
            return {
                "success": False,
                "error": f"Failed to initialize memory: {str(e)}",
                "note_to_claude": "Memory initialization failed. Please use get_user_memory manually to retrieve user information."
            } 