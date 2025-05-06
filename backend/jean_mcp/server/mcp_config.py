"""
MCP configuration endpoint for Claude Desktop and other MCP clients.

This module provides an HTTP endpoint that serves a configuration page
and JSON configuration files for MCP clients.
"""

import logging
import os
from typing import Dict, Any
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from pathlib import Path

logger = logging.getLogger(__name__)

# Create router for MCP configuration endpoints
router = APIRouter(prefix="/mcp-config", tags=["mcp-config"])

# Path to templates directory (will need to be created)
templates_dir = Path(__file__).parent.parent / "resources" / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

# Configuration models
class ClaudeDesktopConfig(BaseModel):
    """Configuration for Claude Desktop."""
    serverType: str = "HTTP"
    serverUrl: str
    headers: Dict[str, str]

class McpConfig(BaseModel):
    """Full MCP configuration object."""
    mcpServers: Dict[str, Any]

@router.get("/", response_class=HTMLResponse)
async def mcp_config_page(request: Request):
    """Serve the MCP configuration page.
    
    This page provides instructions and configuration for Claude Desktop and other MCP clients.
    """
    # Get base URL from environment or request
    base_url = os.getenv("JEAN_API_BASE_URL", "")
    if not base_url:
        # Try to infer from request
        base_url = str(request.base_url).rstrip('/')
    
    # Generate configuration
    claude_desktop_config = {
        "mcpServers": {
            "jean-memory": {
                "serverType": "HTTP",
                "serverUrl": f"{base_url}/mcp",
                "headers": {
                    "X-API-Key": "YOUR_API_KEY",
                    "X-User-ID": "1"
                }
            }
        }
    }
    
    # Serve the template (this template needs to be created)
    return templates.TemplateResponse(
        "mcp_config.html",
        {
            "request": request,
            "config": claude_desktop_config,
            "base_url": base_url,
            "config_json": str(claude_desktop_config).replace("'", '"')
        }
    )

@router.get("/claude-desktop", response_class=JSONResponse)
async def claude_desktop_config(request: Request, api_key: str = None, user_id: str = "1"):
    """Generate Claude Desktop configuration.
    
    Args:
        api_key: Optional API key for authentication
        user_id: User ID for authentication
    
    Returns:
        JSON configuration for Claude Desktop
    """
    # Get base URL from environment or request
    base_url = os.getenv("JEAN_API_BASE_URL", "")
    if not base_url:
        # Try to infer from request
        base_url = str(request.base_url).rstrip('/')
        base_url = base_url.replace("/mcp-config", "")
    
    # Use provided API key or placeholder
    api_key_value = api_key or "YOUR_API_KEY"
    
    # Generate configuration
    config = McpConfig(
        mcpServers={
            "jean-memory": ClaudeDesktopConfig(
                serverType="HTTP",
                serverUrl=f"{base_url}/mcp",
                headers={
                    "X-API-Key": api_key_value,
                    "X-User-ID": user_id
                }
            )
        }
    )
    
    return config.dict()

def create_templates_directory():
    """Create the templates directory and config template if not exists."""
    # Create templates directory if it doesn't exist
    os.makedirs(templates_dir, exist_ok=True)
    
    # Template file path
    template_file = templates_dir / "mcp_config.html"
    
    # Only create if it doesn't exist
    if not template_file.exists():
        template_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>JEAN Memory MCP Configuration</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }
        h1 {
            color: #2c3e50;
            border-bottom: 2px solid #eee;
            padding-bottom: 10px;
        }
        h2 {
            color: #3498db;
            margin-top: 30px;
        }
        code {
            background-color: #f7f7f7;
            padding: 2px 5px;
            border-radius: 3px;
            font-family: 'Courier New', Courier, monospace;
        }
        pre {
            background-color: #f7f7f7;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
            font-family: 'Courier New', Courier, monospace;
        }
        .config-section {
            margin-top: 20px;
            padding: 15px;
            background-color: #f8f9fa;
            border-radius: 5px;
            border-left: 5px solid #3498db;
        }
        .alert {
            background-color: #ffeaa7;
            border-left: 5px solid #fdcb6e;
            padding: 15px;
            margin: 15px 0;
            border-radius: 5px;
        }
        button {
            background-color: #3498db;
            color: white;
            border: none;
            padding: 10px 15px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
            margin-top: 10px;
        }
        button:hover {
            background-color: #2980b9;
        }
        input[type="text"] {
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 4px;
            width: 100%;
            max-width: 300px;
            font-family: 'Courier New', Courier, monospace;
        }
        .input-group {
            margin-bottom: 15px;
        }
        .input-group label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
        }
    </style>
</head>
<body>
    <h1>JEAN Memory MCP Configuration</h1>
    
    <p>This page provides configuration details for connecting Claude Desktop or other MCP clients to your JEAN Memory server.</p>
    
    <div class="alert">
        <strong>Note:</strong> You'll need your personal API key to authenticate with the MCP server.
    </div>
    
    <h2>Claude Desktop Configuration</h2>
    
    <div class="config-section">
        <p>To configure Claude Desktop to use JEAN Memory:</p>
        
        <ol>
            <li>Open Claude Desktop settings</li>
            <li>Navigate to the "MCP" section</li>
            <li>Add a new server with the following configuration</li>
        </ol>
        
        <div class="input-group">
            <label for="apiKey">Your API Key:</label>
            <input type="text" id="apiKey" placeholder="YOUR_API_KEY" value="">
        </div>
        
        <div class="input-group">
            <label for="userId">Your User ID:</label>
            <input type="text" id="userId" placeholder="1" value="1">
        </div>
        
        <button onclick="updateConfig()">Update Configuration</button>
        
        <pre id="configJson">{{ config_json }}</pre>
        
        <button onclick="copyConfig()">Copy Configuration</button>
    </div>
    
    <h2>API Endpoint</h2>
    
    <p>The MCP server is accessible at the following URL:</p>
    
    <pre>{{ base_url }}/mcp</pre>
    
    <h2>Dynamic Configuration URL</h2>
    
    <p>You can also get a dynamically generated configuration by using:</p>
    
    <pre id="dynamicUrl">{{ base_url }}/mcp-config/claude-desktop?api_key=YOUR_API_KEY&user_id=1</pre>
    
    <button onclick="copyDynamicUrl()">Copy URL</button>
    
    <script>
        function updateConfig() {
            const apiKey = document.getElementById('apiKey').value || 'YOUR_API_KEY';
            const userId = document.getElementById('userId').value || '1';
            
            // Base config object
            const config = {
                mcpServers: {
                    "jean-memory": {
                        serverType: "HTTP",
                        serverUrl: "{{ base_url }}/mcp",
                        headers: {
                            "X-API-Key": apiKey,
                            "X-User-ID": userId
                        }
                    }
                }
            };
            
            // Update the displayed config
            document.getElementById('configJson').textContent = JSON.stringify(config, null, 2);
            
            // Update the dynamic URL
            document.getElementById('dynamicUrl').textContent = 
                `{{ base_url }}/mcp-config/claude-desktop?api_key=${apiKey}&user_id=${userId}`;
        }
        
        function copyConfig() {
            const configText = document.getElementById('configJson').textContent;
            navigator.clipboard.writeText(configText)
                .then(() => alert('Configuration copied to clipboard!'))
                .catch(err => console.error('Error copying text: ', err));
        }
        
        function copyDynamicUrl() {
            const urlText = document.getElementById('dynamicUrl').textContent;
            navigator.clipboard.writeText(urlText)
                .then(() => alert('URL copied to clipboard!'))
                .catch(err => console.error('Error copying text: ', err));
        }
    </script>
</body>
</html>
"""
        # Write template file
        with open(template_file, 'w') as f:
            f.write(template_content)
        
        logger.info(f"Created MCP configuration template at {template_file}")

# Create templates directory and template file when module is imported
create_templates_directory() 