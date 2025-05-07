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

logger = logging.getLogger(__name__)

class GoogleAuthRouter:
    def __init__(self):
        self.client_id = os.getenv("GOOGLE_CLIENT_ID")
        self.client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        self.redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:3005/auth/google/callback")
        self.state_store = {}  # In-memory store for CSRF tokens 

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

        return {
            "success": True,
            "auth_url": auth_url
        } 

    async def handle_oauth_callback(self, code: str, state: str) -> Dict[str, Any]:
        """Handle the OAuth callback from Google"""
        # Verify state to prevent CSRF
        if state not in self.state_store:
            logger.error(f"Invalid state parameter: {state}")
            return {"success": False, "message": "Invalid state parameter"}

        user_id = self.state_store.pop(state)
        code_verifier = self.state_store.pop(f"{state}_verifier", None)

        try:
            # Exchange code for access token
            token_url = "https://oauth2.googleapis.com/token"
            token_data = {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": self.redirect_uri,
                "code_verifier": code_verifier
            }

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

            # Store user information in database
            # This is where you would save the user's Google account info
            # For example: await database.store_user_google_info(user_id, user_info)

            # Create a redirect URL with success parameter
            redirect_url = "http://localhost:3005/auth-success?provider=google"
            
            return {
                "success": True,
                "redirect": redirect_url,
                "user_info": {
                    "email": user_info.get("email"),
                    "name": user_info.get("name"),
                    "picture": user_info.get("picture")
                }
            }
        
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error during Google OAuth: {e}")
            return {"success": False, "message": f"Authentication error: {str(e)}"}
        
        except Exception as e:
            logger.error(f"Error during Google OAuth: {e}")
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