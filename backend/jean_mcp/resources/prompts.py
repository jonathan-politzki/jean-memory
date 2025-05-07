"""
MCP prompts for guiding Claude and other LLMs in the JEAN Memory system.

These prompts help the LLM understand how to effectively use the JEAN Memory tools
and provide better responses using contextual information.
"""

import logging
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.prompts import base

logger = logging.getLogger(__name__)

def register_prompts(mcp: FastMCP):
    """Register all MCP prompts with the server."""
    logger.info("Registering MCP prompts...")
    
    @mcp.prompt(name="jean_memory_lookup")
    def jean_memory_lookup_prompt(
        current_query: str,
        reason_for_lookup: str,
        optional_search_topics: str = ""
    ) -> list:
        """Guides the AI to use the access_jean_memory tool effectively.
        Use this prompt when you believe accessing the user's general memory (notes, preferences, etc.)
        could provide crucial context or answer parts of the user's current_query.

        Args:
            current_query: The user's current question or statement to you.
            reason_for_lookup: Clearly explain what information you are hoping to find or what understanding you aim to gain from the memory system to help with the current_query.
            optional_search_topics: Optional comma-separated list of specific topics to focus the memory search on.
        """
        
        return [
            base.UserMessage(f"To help me respond to your query: '{current_query}', I need to understand more about your relevant context or history. "),
            base.AssistantMessage(
                content=f"I will access JEAN Memory. I am looking for: {reason_for_lookup}.",
            )
        ]

    logger.info("MCP Prompts registered.")

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

    @mcp.prompt(name="proactive_memory_creation_guidance")
    def proactive_memory_creation_guidance() -> str:
        """
        Guides the AI to proactively identify and save significant user statements,
        preferences, or important information using the create_jean_memory_entry tool.
        This prompt is for the AI's internal guidance.
        """
        return """
        When interacting with the user, pay close attention to statements that reveal:
        - Strong preferences (e.g., "I love...", "My favorite is...", "I always prefer...")
        - dislikes (e.g., "I hate...", "I never want...")
        - Important facts about the user (e.g., "My project is due next week", "I work as a software engineer")
        - Explicit requests to remember something, even if not phrased as a direct command to create a note.

        If you identify such a statement, you SHOULD consider it an important piece of information to retain.
        To do this, you MUST use the 'create_jean_memory_entry' tool.

        When calling 'create_jean_memory_entry':
        1.  Set 'context_type':
            - Use 'user_preference' for likes, dislikes, favorites, etc.
            - Use 'explicit_note' or a more specific type if appropriate for factual information or tasks.
        2.  Populate 'content':
            - 'preference': A concise summary of the preference (e.g., "User's favorite animal is dogs").
            - 'statement' or 'information': A concise summary of the fact (e.g., "User's project deadline is next week").
            - Include the user's direct quote if it's succinct and captures the essence.
        3.  Populate 'content.importance':
            - Use 'high' if the user uses strong emotional language (love, hate, favorite), repeats the information, or explicitly states its importance.
            - Use 'medium' for general statements of preference or fact.
            - Use 'low' for minor details, if deemed worth saving at all.
        4.  Populate 'content.details':
            - Provide context: Briefly explain why this information is being saved.
            - Include the user's exact phrasing of the key statement.
            - Example: "User stated 'dogs are my favorite animal' after multiple previous mentions of liking dogs."
        5.  For 'source_identifier', you can generate a unique ID or let the system handle it if you're unsure (e.g., "conversation_auto_note_[timestamp]").
        6.  'metadata' can be used for additional tags or categorizations if obvious (e.g., {"category": "personal_preference"}).

        Example Scenario:
        User: "Wow, I absolutely love how responsive this UI is! It's fantastic."
        Your internal action: Decide this is a 'high' importance preference.
        Your tool call:
        create_jean_memory_entry(
            context_type='user_preference',
            content={
                'preference': 'User loves responsive UIs',
                'importance': 'high',
                'details': "User expressed strong positive sentiment: 'Wow, I absolutely love how responsive this UI is! It's fantastic.'"
            },
            source_identifier='conversation_preference_ui_responsiveness_[timestamp]'
        )
        Your response to user (after initiating tool call): "I'm glad you love the responsive UI! I'll remember that."

        DO NOT just say you will remember. If the criteria above are met, the 'create_jean_memory_entry' tool call is the way you remember.
        If the user points out you've forgotten something they consider important, and it aligns with these guidelines, apologize and immediately use 'create_jean_memory_entry' to save it.
        """ 