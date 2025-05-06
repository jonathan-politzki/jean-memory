const express = require('express');
const path = require('path');
const cors = require('cors');
const dotenv = require('dotenv');
const axios = require('axios');

// Load environment variables
dotenv.config();

const app = express();
const PORT = process.env.PORT || 3005;
const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8080';

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.use(express.static(path.join(__dirname, 'public')));

// Proxy the auth Google callback to the backend (simplifies CORS and OAuth flow)
app.get('/auth/google/callback', async (req, res) => {
  try {
    const { code } = req.query;
    if (!code) {
      return res.status(400).send('Missing authorization code');
    }

    // Forward the code to the backend
    const response = await axios.get(`${BACKEND_URL}/auth/google/callback`, {
      params: { code }
    });

    // Get user data from backend response
    const userData = response.data;
    console.log('User data received from backend for redirect:', userData);

    // Redirect to the profile page with user data using consistent parameter names
    res.redirect(`/profile.html?jean_user_id=${userData.user_id}&jean_api_key=${userData.api_key}`);
  } catch (error) {
    console.error('Auth callback error:', error);
    res.status(500).send('Authentication failed. Please try again.');
  }
});

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