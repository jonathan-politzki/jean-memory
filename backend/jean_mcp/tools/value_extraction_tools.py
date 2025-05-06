"""
MCP tools for extracting user values and preferences from context in the JEAN Memory system.

These tools use Google's Gemini Pro model to analyze a user's context and conversations
to extract implicit and explicit values, preferences, and priorities.
"""

import logging
import os
from typing import List, Dict, Any, Optional
import google.generativeai as genai
from mcp.server.fastmcp import FastMCP, Context

logger = logging.getLogger(__name__)

# Configure Gemini API
def setup_gemini():
    """Set up the Gemini API client."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.warning("GEMINI_API_KEY environment variable not set. Value extraction tools will not work.")
        return False
    
    genai.configure(api_key=api_key)
    return True

def register_value_extraction_tools(mcp: FastMCP):
    """Register all value extraction tools with the MCP server."""
    logger.info("Registering value extraction tools with MCP server")
    
    # Check if Gemini is properly configured
    gemini_available = setup_gemini()
    
    @mcp.tool()
    async def extract_user_values(
        topic: str,
        context_limit: int = 20,
        ctx: Context = None
    ) -> Dict[str, Any]:
        """Extract user values and preferences related to a specific topic.
        
        This tool analyzes a user's notes and context to identify what they value
        about a specific topic. It uses Gemini to perform deep analysis of contextual data.
        
        Args:
            topic: The topic to extract values for (e.g., "work", "technology", "health")
            context_limit: Maximum number of context items to analyze
            ctx: MCP context object
        
        Returns:
            Dictionary with extracted values and preferences
        """
        if not gemini_available:
            return {"success": False, "error": "Gemini API not configured. Set GEMINI_API_KEY environment variable."}
        
        if not ctx or not ctx.request_context.lifespan_context.db:
            return {"success": False, "error": "Database not available"}
        
        db = ctx.request_context.lifespan_context.db
        user_id = ctx.request_context.lifespan_context.user_id
        tenant_id = ctx.request_context.lifespan_context.tenant_id
        
        if not user_id:
            return {"success": False, "error": "User ID not provided"}
        
        try:
            # Search for relevant notes on the topic
            results = await db.search_context(
                user_id=user_id,
                tenant_id=tenant_id,
                context_type="notes",
                query=topic,
                limit=context_limit
            )
            
            # If we don't have enough topic-specific notes, get recent notes too
            if len(results) < 5:
                recent_results = await db.get_recent_context(
                    user_id=user_id,
                    tenant_id=tenant_id,
                    context_type="notes",
                    limit=context_limit - len(results)
                )
                # Combine results, avoiding duplicates
                existing_ids = [r.get("id") for r in results]
                for item in recent_results:
                    if item.get("id") not in existing_ids:
                        results.append(item)
            
            if not results:
                return {
                    "success": True,
                    "values": [],
                    "message": f"No context found related to '{topic}'"
                }
            
            # Format context for Gemini
            context_text = f"# User Context Related to '{topic}'\n\n"
            for i, item in enumerate(results):
                context_text += f"## Note {i+1}\n"
                context_text += f"{item.get('content')}\n\n"
            
            # Create prompt for Gemini
            prompt = f"""
            Based on the following user context, identify the user's values, preferences, and priorities related to '{topic}'.
            
            Consider:
            1. Explicit statements about preferences
            2. Implicit values revealed by their actions or interests
            3. Consistent patterns across multiple contexts
            4. Any strong opinions or emotional reactions
            
            Format your response as a JSON object with these fields:
            1. "core_values" - List of 3-5 core values the user seems to hold about this topic
            2. "preferences" - List of specific preferences the user has expressed
            3. "priorities" - What the user seems to prioritize most about this topic
            4. "confidence" - Your confidence level in these observations (low, medium, high)
            
            USER CONTEXT:
            {context_text}
            """
            
            # Call Gemini to analyze the context
            gemini_model = genai.GenerativeModel('gemini-pro')
            response = gemini_model.generate_content(prompt)
            
            # Process and structure the response
            try:
                # Try to extract JSON directly if possible
                import json
                from json import JSONDecodeError
                
                try:
                    # First try to parse the entire response
                    values_data = json.loads(response.text)
                except JSONDecodeError:
                    # If that fails, look for JSON block markers and extract the JSON
                    import re
                    json_match = re.search(r'```json\n(.*?)\n```', response.text, re.DOTALL)
                    if json_match:
                        values_data = json.loads(json_match.group(1))
                    else:
                        # Last resort, create a basic structure with the raw text
                        values_data = {
                            "core_values": [],
                            "preferences": [],
                            "priorities": [],
                            "confidence": "low",
                            "raw_response": response.text
                        }
            except Exception as json_error:
                logger.exception(f"Error parsing Gemini response: {json_error}")
                values_data = {
                    "core_values": [],
                    "preferences": [],
                    "priorities": [],
                    "confidence": "low",
                    "raw_response": response.text
                }
            
            return {
                "success": True,
                "topic": topic,
                "values": values_data,
                "context_count": len(results)
            }
            
        except Exception as e:
            logger.exception(f"Error extracting user values: {e}")
            return {"success": False, "error": str(e)}
    
    @mcp.tool()
    async def summarize_user_preference_history(
        preference_type: str,
        ctx: Context = None
    ) -> Dict[str, Any]:
        """Summarize how a user's preferences have evolved over time.
        
        This tool analyzes notes chronologically to identify how preferences have changed.
        
        Args:
            preference_type: The type of preference to analyze (e.g., "technology", "books")
            ctx: MCP context object
        
        Returns:
            Dictionary with a summary of preference evolution
        """
        if not gemini_available:
            return {"success": False, "error": "Gemini API not configured. Set GEMINI_API_KEY environment variable."}
        
        if not ctx or not ctx.request_context.lifespan_context.db:
            return {"success": False, "error": "Database not available"}
        
        db = ctx.request_context.lifespan_context.db
        user_id = ctx.request_context.lifespan_context.user_id
        tenant_id = ctx.request_context.lifespan_context.tenant_id
        
        if not user_id:
            return {"success": False, "error": "User ID not provided"}
        
        try:
            # Search for relevant notes on the preference type
            results = await db.search_context(
                user_id=user_id,
                tenant_id=tenant_id,
                context_type="notes",
                query=preference_type,
                limit=30
            )
            
            if not results:
                return {
                    "success": True,
                    "summary": f"No history found related to preferences about '{preference_type}'",
                    "timeline": []
                }
            
            # Sort by date
            results.sort(key=lambda x: x.get("created_at", ""))
            
            # Format context for Gemini
            context_text = f"# User Preference History Related to '{preference_type}'\n\n"
            for i, item in enumerate(results):
                date = item.get("created_at", "Unknown date")
                context_text += f"## Note from {date}\n"
                context_text += f"{item.get('content')}\n\n"
            
            # Create prompt for Gemini
            prompt = f"""
            Based on the following chronological user context, analyze how the user's preferences about '{preference_type}' have evolved over time.
            
            Format your response as a JSON object with these fields:
            1. "summary" - A paragraph summarizing how preferences have changed over time
            2. "timeline" - Array of objects, each with:
               - "period" - Approximate time period
               - "preferences" - Key preferences during this period
               - "trigger" - What might have triggered any change (if apparent)
            3. "consistency" - Assessment of how consistent the user has been (high, medium, low)
            
            USER CONTEXT (Chronological Order):
            {context_text}
            """
            
            # Call Gemini to analyze the preference history
            gemini_model = genai.GenerativeModel('gemini-pro')
            response = gemini_model.generate_content(prompt)
            
            # Process and structure the response
            try:
                import json
                from json import JSONDecodeError
                
                try:
                    # First try to parse the entire response
                    preference_data = json.loads(response.text)
                except JSONDecodeError:
                    # If that fails, look for JSON block markers and extract the JSON
                    import re
                    json_match = re.search(r'```json\n(.*?)\n```', response.text, re.DOTALL)
                    if json_match:
                        preference_data = json.loads(json_match.group(1))
                    else:
                        # Last resort, create a basic structure with the raw text
                        preference_data = {
                            "summary": "Could not parse a structured summary.",
                            "timeline": [],
                            "consistency": "unknown",
                            "raw_response": response.text
                        }
            except Exception as json_error:
                logger.exception(f"Error parsing Gemini response: {json_error}")
                preference_data = {
                    "summary": "Could not parse a structured summary.",
                    "timeline": [],
                    "consistency": "unknown",
                    "raw_response": response.text
                }
            
            return {
                "success": True,
                "preference_type": preference_type,
                "analysis": preference_data,
                "note_count": len(results)
            }
            
        except Exception as e:
            logger.exception(f"Error analyzing preference history: {e}")
            return {"success": False, "error": str(e)}
            
    # Register resource endpoint for value extraction
    @mcp.resource("values://{topic}")
    async def values_resource(topic: str) -> str:
        """Get extracted values as a formatted resource.
        
        This allows clients to directly access value extraction through a resource URI.
        """
        result = await extract_user_values(topic=topic, ctx=None)
        if not result.get("success"):
            return f"Error extracting values: {result.get('error')}"
        
        values_data = result.get("values", {})
        if not values_data or not values_data.get("core_values"):
            return f"Could not extract clear values related to '{topic}'"
        
        output = f"# Your Values Related to '{topic}'\n\n"
        
        # Core values section
        output += "## Core Values\n\n"
        for value in values_data.get("core_values", []):
            output += f"- {value}\n"
        
        # Preferences section
        output += "\n## Preferences\n\n"
        for pref in values_data.get("preferences", []):
            output += f"- {pref}\n"
        
        # Priorities section
        output += "\n## Priorities\n\n"
        for priority in values_data.get("priorities", []):
            output += f"- {priority}\n"
        
        # Confidence note
        output += f"\n*Confidence in this analysis: {values_data.get('confidence', 'medium')}*\n"
        
        return output 