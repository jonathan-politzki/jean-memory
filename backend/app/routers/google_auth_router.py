import os
import logging
import httpx
import json
from fastapi import APIRouter, HTTPException, Request, Response, Depends
from fastapi.responses import RedirectResponse, JSONResponse
import uuid
from typing import Dict, Optional, Any
import base64
import hashlib
import secrets
import database  # Import the database singleton module
from database.context_storage import ContextDatabase # Import for type hinting

logger = logging.getLogger(__name__)

class GoogleAuthRouter:
    def __init__(self, db: ContextDatabase):
        self.db = db
        self.client_id = os.getenv("GOOGLE_CLIENT_ID")
        self.client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        # REVERT HARDCODING:
        # self.redirect_uri = "http://localhost:3005/auth/google/callback.html" # This was for testing
        self.redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:3005/auth/google/callback.html") # Restore original
        self.state_store = {}  # In-memory store for CSRF tokens
        self.processed_codes = set()  # Track codes we've already processed

    async def get_oauth_url(self, user_id: str) -> Dict[str, Any]:
        """Generate OAuth URL for Google authentication"""
        # Create a state parameter to prevent CSRF
        state = str(uuid.uuid4())
        self.state_store[state] = user_id

        # Generate code verifier and challenge for PKCE
        code_verifier = secrets.token_urlsafe(64)
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode()).digest()
        ).decode().rstrip("=")

        # Store the code verifier for later
        self.state_store[f"{state}_verifier"] = code_verifier

        logger.info(f"[AUTH_DEBUG] Using redirect_uri for Google OAuth: {self.redirect_uri}")

        # Build the authorization URL
        auth_url = (
            "https://accounts.google.com/o/oauth2/v2/auth"
            f"?client_id={self.client_id}"
            "&response_type=code"
            f"&redirect_uri={self.redirect_uri}"
            "&scope=openid%20email%20profile"
            f"&state={state}"
            f"&code_challenge={code_challenge}"
            "&code_challenge_method=S256"
        )

        logger.info(f"[AUTH_DEBUG] Generated Google OAuth URL: {auth_url}")

        return {
            "success": True,
            "auth_url": auth_url
        }

    async def handle_oauth_callback(self, code: str, state: str) -> Dict[str, Any]:
        """Handle the OAuth callback from Google"""
        # For development, make state validation optional
        dev_mode = os.getenv("DEV_MODE", "false").lower() == "true"
        
        # Check if we've already processed this auth code (same code used multiple times)
        if code in self.processed_codes:
            logger.info(f"Auth code '{code}' has already been processed.") # More specific log
            
            if dev_mode:
                logger.warning(f"DEV_MODE: Auth code '{code}' already processed. Returning 409 Conflict to indicate potential frontend/redirect issue.")
                return JSONResponse( # Explicitly return JSONResponse with 409
                    status_code=409, 
                    content={"success": False, "message": f"DEV_MODE: Authorization code '{code}' has already been used. This could indicate an issue with how the frontend handles the callback or redirects."}
                )
            else:
                logger.warning(f"Auth code '{code}' already processed and not in DEV_MODE. Returning 409 Conflict.") # More specific log
                return JSONResponse( # Explicitly return JSONResponse with 409
                    status_code=409,
                    content={"success": False, "message": "Authorization code has already been used."}
                )
        
        # Verify state if present or use dev_mode fallback
        valid_state = state in self.state_store
        user_id = None
        code_verifier = None
        
        if valid_state:
            # We have a valid state, use it
            user_id = self.state_store.pop(state)
            code_verifier = self.state_store.pop(f"{state}_verifier", None)
            logger.info(f"Found valid state {state} for user {user_id}")
        elif dev_mode:
            # Dev mode fallback
            logger.warning(f"Dev mode: Proceeding without valid state. Using default user ID.")
            user_id = "dev-user"
        else:
            # No valid state and not in dev mode - reject
            logger.error(f"Invalid state parameter: {state}")
            return {"success": False, "message": "Invalid state parameter"}

        try:
            # Exchange code for access token
            token_url = "https://oauth2.googleapis.com/token"
            token_data = {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": self.redirect_uri
            }
            
            # Add code_verifier if we have it
            if code_verifier:
                token_data["code_verifier"] = code_verifier
                
            logger.info(f"Exchanging code for token with redirect_uri: {self.redirect_uri}")
            
            try:
                async with httpx.AsyncClient() as client:
                    token_response = await client.post(token_url, data=token_data)
                    token_response.raise_for_status()
                    token_info = token_response.json()
                    
                    # Get user info using the access token
                    headers = {"Authorization": f"Bearer {token_info['access_token']}"}
                    user_info_response = await client.get(
                        "https://www.googleapis.com/oauth2/v3/userinfo",
                        headers=headers
                    )
                    user_info_response.raise_for_status()
                    user_info = user_info_response.json()
                    
                    # Cache token and user info to avoid duplicate token exchanges
                    self.state_store[f"{state}_token_info"] = token_info
                    self.state_store[f"{state}_user_info"] = user_info
                    
            except httpx.HTTPStatusError as e:
                error_details = "Unknown error"
                try:
                    error_details = e.response.json()
                except Exception:
                    try:
                        error_details = e.response.text
                    except Exception:
                        pass
                
                logger.error(f"HTTP error during Google OAuth: {e} - Details: {error_details}")
                
                # If we're in dev mode and this is the second attempt with same code, use the demo user
                if dev_mode:
                    logger.warning("Google OAuth HTTP error occurred in DEV_MODE. Returning actual error instead of demo user.")
                    return {"success": False, "message": f"Google OAuth API Error (DEV_MODE active): {error_details}"}
                
                return {"success": False, "message": f"Authentication error: {str(e)}"}

            # Create or get user with their Google ID
            tenant_id = os.getenv("JEAN_TENANT_ID", "default")
            db_user_id, api_key = await self.db.create_or_get_user(
                tenant_id=tenant_id,
                google_id=user_info.get("sub"),
                email=user_info.get("email")
            )
            
            logger.info(f"User authenticated: ID={db_user_id}, Email={user_info.get('email')}")

            # Track this code as processed to prevent reuse
            self.processed_codes.add(code)

            return {
                "success": True,
                "user_info": {
                    "user_id": db_user_id,
                    "email": user_info.get("email"),
                    "name": user_info.get("name"), 
                    "picture": user_info.get("picture"),
                    "api_key": api_key
                }
            }
        
        except httpx.HTTPStatusError as e:
            error_details = "Unknown error"
            try:
                error_details = e.response.json()
            except Exception:
                try:
                    error_details = e.response.text
                except Exception:
                    pass
            
            logger.error(f"HTTP error during Google OAuth: {e} - Details: {error_details}")
            
            # If we're in dev mode, use the demo user
            if dev_mode:
                logger.warning("Google OAuth HTTP error occurred in DEV_MODE. Returning actual error instead of demo user.")
                return {"success": False, "message": f"Google OAuth API Error (DEV_MODE active): {error_details}"}
            
            return {"success": False, "message": f"Authentication error: {str(e)}"}
        
        except Exception as e:
            logger.error(f"Error during Google OAuth: {e}")
            
            # If we're in dev mode, use the demo user
            if dev_mode:
                logger.warning("General Google OAuth error occurred in DEV_MODE. Returning actual error instead of demo user.")
                return {"success": False, "message": f"General Google OAuth Error (DEV_MODE active): {str(e)}"}
            
            return {"success": False, "message": f"Authentication error: {str(e)}"}

    async def check_connection_status(self, user_id: str) -> Dict[str, Any]:
        """Check if user has connected their Google account"""
        # Check database for user's Google connection
        # For example: connected = await database.check_google_connection(user_id)
        
        # For now, return a placeholder status
        return {
            "success": True,
            "connected": False,  # Replace with actual database check
            "message": "Google connection status retrieved"
        }

    async def disconnect(self, user_id: str) -> Dict[str, Any]:
        """Disconnect Google account"""
        # Remove Google connection from database
        # For example: await database.remove_google_connection(user_id)
        
        return {
            "success": True,
            "message": "Google account disconnected successfully"
        } 