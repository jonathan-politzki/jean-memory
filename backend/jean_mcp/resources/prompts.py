"""
MCP prompts for guiding Claude and other LLMs in the JEAN Memory system.

These prompts help the LLM understand how to effectively use the JEAN Memory tools
and provide better responses using contextual information.
"""

import logging
from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)

def register_prompts(mcp: FastMCP):
    """Register all prompts with the MCP server."""
    logger.info("Registering prompts with MCP server")
    
    @mcp.prompt("system_introduction")
    def system_introduction() -> str:
        """Introduction prompt explaining what JEAN Memory is."""
        return """
        I am equipped with a personal memory system called JEAN Memory. 
        This system stores your notes, GitHub activity, and other personal context.
        
        I can search, retrieve, and create notes to help maintain a persistent memory of our conversations.
        When you ask me questions about things we've discussed before or your personal context,
        I'll automatically search your memory to provide more accurate and personalized responses.
        
        You can explicitly ask me to:
        - Save important information as notes
        - Search for notes on specific topics
        - Retrieve your recent notes
        - Access your GitHub repositories and activity
        
        I'll also proactively use your memory when relevant to our conversation.
        """
    
    @mcp.prompt("note_creation_guide")
    def note_creation_guide() -> str:
        """Prompt explaining how to effectively create notes."""
        return """
        To create effective notes in your JEAN Memory:
        
        1. I can create a note with key information from our conversation
        2. You can explicitly ask me to save specific information
        3. You can provide tags to organize your notes
        
        Examples:
        - "Save this meeting summary as a note"
        - "Create a note about this programming technique"
        - "Remember this information about my project preferences"
        
        When creating a note, I'll confirm what was saved and how to retrieve it later.
        """
    
    @mcp.prompt("search_guidance")
    def search_guidance() -> str:
        """Prompt explaining how to effectively search for information."""
        return """
        When searching your JEAN Memory:
        
        1. Try to use specific keywords related to what you're looking for
        2. I can search across all your notes and saved context
        3. If you don't find what you're looking for, try alternative terms
        
        Examples:
        - "Find information about my React project"
        - "Search my notes for vacation plans"
        - "Do I have any notes about database design?"
        
        I'll present the most relevant results and can help refine your search if needed.
        """
    
    @mcp.prompt("github_integration_guide")
    def github_integration_guide() -> str:
        """Prompt explaining how to use GitHub integration."""
        return """
        To use the GitHub integration with JEAN Memory:
        
        1. I can retrieve information about your repositories
        2. I can show your recent GitHub activity
        3. This helps maintain context about your coding projects
        
        Examples:
        - "Show me my recent GitHub activity"
        - "List my top repositories"
        - "What have I been working on in GitHub lately?"
        
        Note: GitHub integration requires you to have configured your GitHub token in settings.
        """
    
    @mcp.prompt("value_extraction_prompt")
    def value_extraction_prompt() -> str:
        """Prompt for extracting a user's values from conversation history."""
        return """
        Based on our conversation history and the notes in your JEAN Memory, 
        I'll try to identify what seems important to you regarding this topic.
        
        I'll consider:
        1. Explicit statements about your preferences
        2. Recurring themes in our discussions
        3. Past decisions you've made and your reasoning
        4. Projects and topics you've shown interest in
        
        This helps me provide more personalized assistance aligned with your values.
        """
    
    @mcp.prompt("memory_retrieval_strategy")
    def memory_retrieval_strategy() -> str:
        """Strategy prompt for effective memory retrieval."""
        return """
        When retrieving information from JEAN Memory:
        
        1. First try semantic search with key terms from the user's question
        2. If initial results aren't relevant, expand search terms
        3. Consider time relevance - recent notes may be more important
        4. Look for patterns across multiple notes
        5. If multiple memory sources exist, prioritize:
           - Explicit notes on the topic
           - Recent GitHub activity if code-related
           - Historical conversation context
           
        Present the most relevant information concisely and explain how it relates to the user's question.
        """ 