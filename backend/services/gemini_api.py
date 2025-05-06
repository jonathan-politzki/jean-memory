import google.generativeai as genai
import os
import asyncio
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class GeminiAPI:
    """Service for interacting with the Google Gemini API."""

    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("GEMINI_API_KEY is required.")
        try:
            genai.configure(api_key=api_key)
            # Check if model is available, otherwise log warning
            # Note: Listing models might require specific permissions
            # or might change. Basic check is configuring.
            logger.info("Google Generative AI client configured.")
        except Exception as e:
            logger.exception(f"Failed to configure Google Generative AI: {e}")
            raise

        # Consider adding a cache (e.g., using cachetools) if needed
        # self.cache = {}

    def _format_github(self, github_data: List[Dict[str, Any]]) -> str:
        """Format GitHub data for Gemini API prompt."""
        formatted = "GITHUB REPOSITORIES:\n\n"
        for repo in github_data:
            formatted += f"Repo: {repo.get('name', 'N/A')}\n"
            desc = repo.get('description')
            if desc:
                formatted += f"Description: {desc}\n"
            files = repo.get('files', [])
            if files:
                 formatted += "Files:\n"
                 for file in files[:5]: # Limit files shown per repo for brevity
                    path = file.get('path', 'N/A')
                    content_preview = file.get('content', '')[:500] # Limit content preview
                    formatted += f"  - Path: {path}\n"
                    if content_preview:
                        formatted += f"    Content Preview: {content_preview}...\n"
            formatted += "\n"
        return formatted

    def _format_notes(self, notes_data: List[Dict[str, Any]]) -> str:
        """Format notes data for Gemini API prompt."""
        formatted = "PERSONAL NOTES:\n\n"
        for note in notes_data:
            title = note.get('title', 'Untitled')
            content = note.get('content', '')[:1000] # Limit content preview
            timestamp = note.get('timestamp', 'N/A')
            formatted += f"Note Title: {title}\n"
            formatted += f"Timestamp: {timestamp}\n"
            formatted += f"Content: {content}...\n\n"
        return formatted

    def _format_values(self, values_data: List[Dict[str, Any]]) -> str:
        """Format values data for Gemini API prompt."""
        formatted = "PERSONAL VALUES & PREFERENCES:\n\n"
        for value in values_data:
            key = value.get('key', 'N/A')
            val = value.get('value', 'N/A')
            source = value.get('source', 'N/A')
            formatted += f"- {key}: {val} (Source: {source})\n"
        return formatted

    def _format_conversations(self, conversations_data: List[Dict[str, Any]]) -> str:
        """Format conversations data for Gemini API prompt."""
        formatted = "CONVERSATION HISTORY SNIPPETS:\n\n"
        for conv in conversations_data:
            timestamp = conv.get('timestamp', 'N/A')
            speaker = conv.get('speaker', 'N/A')
            text = conv.get('text', '')[:500] # Limit snippet length
            formatted += f"[{timestamp}] {speaker}: {text}...\n"
        return formatted

    def _format_comprehensive(self, context_data: Dict[str, List[Dict[str, Any]]]) -> str:
        """Format multiple context types for a comprehensive query."""
        formatted = "COMPREHENSIVE CONTEXT:\n\n"
        if github_data := context_data.get("github"):
            formatted += self._format_github(github_data)
            formatted += "---\n"
        if notes_data := context_data.get("notes"):
            formatted += self._format_notes(notes_data)
            formatted += "---\n"
        if values_data := context_data.get("values"):
            formatted += self._format_values(values_data)
            formatted += "---\n"
        if conversations_data := context_data.get("conversations"):
            formatted += self._format_conversations(conversations_data)
        return formatted

    async def process(self, context_type: str, context_data: Any, query: str) -> str:
        """Process context with Gemini API based on type."""
        system_prompt = "You are an AI assistant analyzing personal context to answer a user query."
        formatted_context = ""

        try:
            if context_type == "github":
                formatted_context = self._format_github(context_data)
                system_prompt = "You are analyzing the user's GitHub repositories and code."
            elif context_type == "notes":
                formatted_context = self._format_notes(context_data)
                system_prompt = "You are analyzing the user's personal notes and documents."
            elif context_type == "values":
                formatted_context = self._format_values(context_data)
                system_prompt = "You are analyzing the user's stated personal values and preferences."
            elif context_type == "conversations":
                formatted_context = self._format_conversations(context_data)
                system_prompt = "You are analyzing the user's past conversation history."
            elif context_type == "comprehensive":
                 formatted_context = self._format_comprehensive(context_data)
                 system_prompt = "You are analyzing comprehensive personal context from multiple sources."
            else:
                logger.warning(f"Unknown context type '{context_type}' for Gemini processing.")
                # Fallback or default formatting?
                formatted_context = str(context_data) # Basic fallback
                system_prompt = "You are analyzing personal context."

            if not formatted_context:
                 logger.warning(f"No context data provided or formatted for type '{context_type}'. Cannot call Gemini.")
                 return "Error: No context data available to process."

            prompt = f"""
            {system_prompt}

            USER QUERY: {query}

            AVAILABLE CONTEXT INFORMATION:
            {formatted_context}

            Based *only* on the context information provided above, answer the user query concisely. Focus on extracting directly relevant facts or summaries. If the context doesn't contain the answer, state that explicitly.
            """

            logger.info(f"Calling Gemini API for context type '{context_type}'...")
            # Use gemini-1.5-flash for potentially faster/cheaper processing if sufficient
            model = genai.GenerativeModel('gemini-1.5-pro-latest') # Or 'gemini-1.5-flash-latest'

            # Run generate_content in a separate thread to avoid blocking asyncio event loop
            response = await asyncio.to_thread(
                model.generate_content,
                prompt
            )

            logger.info(f"Received response from Gemini for type '{context_type}'.")
            # Consider adding more robust error checking on response object
            return response.text

        except Exception as e:
            logger.exception(f"Error processing context type '{context_type}' with Gemini: {e}")
            # Return a user-friendly error message
            return f"Error: Could not process context due to an internal error with the AI model." 