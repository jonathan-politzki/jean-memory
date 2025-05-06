"""
Database singleton module for JEAN memory.
This ensures a single shared database connection is used across the application.
"""

import logging
from typing import Optional
from .context_storage import ContextDatabase

logger = logging.getLogger(__name__)

# Global database instance (singleton)
_db_instance: Optional[ContextDatabase] = None

async def initialize_db(connection_string: str) -> ContextDatabase:
    """Initialize the global database instance if not already initialized.
    
    Args:
        connection_string: Database connection string
        
    Returns:
        The global database instance
    """
    global _db_instance
    
    if _db_instance is None:
        logger.info("Creating global database singleton instance")
        _db_instance = ContextDatabase(connection_string)
        await _db_instance.initialize()
        logger.info("Global database singleton initialized and ready")
    else:
        logger.info("Using existing database singleton instance")
    
    return _db_instance

def get_db() -> Optional[ContextDatabase]:
    """Get the global database instance.
    
    Returns:
        The global database instance, or None if not initialized
    """
    return _db_instance

async def close_db() -> None:
    """Close the global database connection."""
    global _db_instance
    
    if _db_instance is not None:
        logger.info("Closing global database singleton connection")
        await _db_instance.close()
        _db_instance = None
        logger.info("Global database singleton connection closed") 