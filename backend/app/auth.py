from fastapi import Depends, HTTPException, Security
from fastapi.security import APIKeyHeader
import os
from typing import Optional

# Define the API key header
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# Define user ID header
user_id_header = APIKeyHeader(name="X-User-ID", auto_error=False)

async def verify_api_key(api_key: Optional[str] = Security(api_key_header)) -> bool:
    """
    Verify the API key provided in the header.
    In a real application, you would validate against a database of valid keys.
    For development, we'll check against an environment variable or allow any key.
    """
    # Get API key from environment (if set)
    valid_api_key = os.getenv("JEAN_API_KEY")
    
    # If no API key environment variable is set, accept any non-empty key for development
    if not valid_api_key:
        return bool(api_key)  # Accept any non-empty key
    
    # Otherwise, validate against the environment variable
    if api_key != valid_api_key:
        raise HTTPException(
            status_code=403, 
            detail="Invalid API key"
        )
    
    return True

async def get_user_id(
    api_key_valid: bool = Depends(verify_api_key),
    user_id: Optional[str] = Security(user_id_header)
) -> str:
    """
    Get the user ID from the header after validating the API key.
    """
    if not api_key_valid:
        raise HTTPException(
            status_code=403,
            detail="Invalid API key"
        )
    
    if not user_id:
        # If no user ID provided in header, use default from environment or "1"
        user_id = os.getenv("JEAN_USER_ID", "1")
    
    return user_id 