const express = require('express');
const path = require('path');
const cors = require('cors');
const dotenv = require('dotenv');
const axios = require('axios');

// Load environment variables
dotenv.config();

const app = express();
const PORT = process.env.PORT || 3005;

// Determine the backend URL with fallbacks for different environments
const BACKEND_URL = process.env.BACKEND_URL || 
                   (process.env.NODE_ENV === 'production' ? 'http://backend:8000' : 'http://localhost:8000');

console.log(`Using backend URL: ${BACKEND_URL}`);

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.use(express.static(path.join(__dirname, 'public')));

/*
// Proxy the auth Google callback to the backend (simplifies CORS and OAuth flow)
// DEPRECATED: This route is maintained for backward compatibility
// The preferred approach is now to use the HTML file at /auth/google/callback.html
app.get('/auth/google/callback', async (req, res) => {
  try {
    const { code, state } = req.query;
    if (!code) {
      return res.status(400).send('Missing authorization code');
    }

    console.log(`Received auth callback. Forwarding to backend at ${BACKEND_URL}/api/auth/google/callback`);
    console.log(`WARNING: Using deprecated callback route. Please switch to HTML-based callback.`);

    // Forward the code and state to the backend
    const response = await axios.get(`${BACKEND_URL}/api/auth/google/callback`, {
      params: { code, state },
      timeout: 10000 // 10 second timeout
    });

    // Get user data from backend response
    const responseData = response.data;
    console.log('Auth callback response received:', JSON.stringify(responseData));

    if (!responseData.success) {
      console.error('Authentication failed:', responseData.message);
      return res.status(400).send(`Authentication failed: ${responseData.message || 'Unknown error'}`);
    }

    // Store user info in a temporary script that will be executed on the auth-success page
    // This allows us to securely pass the user info to the client-side JavaScript
    const userInfo = responseData.user_info;
    const userInfoJson = JSON.stringify(userInfo).replace(/</g, '\\u003c').replace(/>/g, '\\u003e').replace(/&/g, '\\u0026').replace(/'/g, '\\u0027').replace(/"/g, '\\"');

    console.log('Storing user info and redirecting to auth-success page');
    
    // Check if this is a repeated callback to prevent loops
    const isRepeated = req.query.processed === 'true';
    if (isRepeated) {
      console.log('Detected repeated auth callback, redirecting to dashboard instead');
      const dashboardScript = `
        <script>
          console.log("Auth already processed, going to dashboard");
          window.location.href = '/dashboard.html';
        </script>
      `;
      return res.send(dashboardScript);
    }
    
    // Redirect user to the HTML-based callback which is now preferred
    return res.redirect(`/auth/google/callback.html${req.url.substring(req.url.indexOf('?'))}`);
  } catch (error) {
    console.error('Auth callback error:', error.message);
    if (error.response) {
      console.error('Backend response:', error.response.status, error.response.data);
    } else if (error.request) {
      console.error('No response received from backend');
    } else {
      console.error('Error setting up request:', error.message);
    }
    
    // For development, fall back to a demo user if the backend is unreachable
    if (process.env.NODE_ENV !== 'production') {
      console.log('DEVELOPMENT MODE: Falling back to demo user...');
      
      const demoUser = {
        user_id: 'demo-user-1',
        email: 'demo@example.com',
        name: 'Demo User',
        picture: '/img/user-avatar.png',
        api_key: 'demo-api-key-123'
      };
      
      const demoUserJson = JSON.stringify(demoUser)
        .replace(/</g, '\\u003c')
        .replace(/>/g, '\\u003e')
        .replace(/&/g, '\\u0026')
        .replace(/'/g, '\\u0027').replace(/"/g, '\\"');
        
      const demoScript = `
        <script>
          console.log("DEMO MODE: Using demo user");
          localStorage.setItem('tempUserInfo', "${demoUserJson}");
          window.location.href = '/auth-success.html?provider=google&demo=true';
        </script>
      `;
      
      return res.send(demoScript);
    }
    
    // Provide a more user-friendly error page
    const errorScript = `
      <html>
      <head>
        <title>Authentication Error</title>
        <style>
          body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
          .error-container { max-width: 600px; margin: 0 auto; }
          .error-icon { font-size: 64px; color: #e53e3e; }
          .error-title { color: #e53e3e; margin-bottom: 20px; }
          .error-message { margin-bottom: 30px; color: #4a5568; }
          .error-details { text-align: left; padding: 10px; background: #f8f8f8; border-radius: 5px; font-family: monospace; margin-bottom: 20px; }
          .btn { padding: 10px 20px; background-color: #4a6cff; color: white; border: none; 
                border-radius: 5px; text-decoration: none; cursor: pointer; }
        </style>
      </head>
      <body>
        <div class="error-container">
          <div class="error-icon">⚠️</div>
          <h1 class="error-title">Authentication Failed</h1>
          <p class="error-message">
            We encountered a problem connecting to the authentication server. 
            Please try again later or contact support if the problem persists.
          </p>
          <div class="error-details">
            Error: ${error.message?.replace(/</g, '&lt;').replace(/>/g, '&gt;') || "Unknown error"}
          </div>
          <a href="/" class="btn">Return to Home</a>
          <a href="/auth-debug.html" class="btn" style="background-color: #4299e1;">Debug Authentication</a>
        </div>
        <script>
          console.error('Auth error: ${error.message?.replace(/"/g, '\\"') || "Unknown error"}');
          setTimeout(() => {
            window.location.href = '/?auth_error=true';
          }, 30000);
        </script>
      </body>
      </html>
    `;
    res.status(500).send(errorScript);
  }
});
*/

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({ status: 'ok' });
});

// API endpoint to get MCP configuration
app.get('/api/mcp-config', (req, res) => {
  const apiKey = req.query.api_key;
  if (!apiKey) {
    return res.status(400).json({ error: 'API key is required' });
  }

  // Construct the MCP configuration
  const mcpConfig = {
    mcp_server_url: `${BACKEND_URL}/mcp`,
    api_key: apiKey
  };

  res.json(mcpConfig);
});

// Start the server
app.listen(PORT, () => {
  console.log(`JEAN Frontend server running on port ${PORT}`);
  console.log(`Backend URL: ${BACKEND_URL}`);
}); 