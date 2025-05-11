const express = require('express');
const path = require('path');
const cors = require('cors');
const dotenv = require('dotenv');
const axios = require('axios');
const fs = require('fs');
const {GoogleAuth} = require('google-auth-library');

// Load environment variables
dotenv.config();

const app = express();
const PORT = process.env.PORT || 3005;
const ACTUAL_BACKEND_URL = process.env.BACKEND_URL;
const DEV_MODE = process.env.NODE_ENV === 'development' || process.env.DEV_MODE === 'true';

console.log(`JEAN Frontend server starting on port ${PORT}`);
if (!ACTUAL_BACKEND_URL) {
    console.error('FATAL ERROR: BACKEND_URL environment variable not set!');
    process.exit(1);
}
console.log(`Proxying API requests to: ${ACTUAL_BACKEND_URL}`);
if (DEV_MODE) {
    console.log('Development mode: enabled - using mock responses for authentication');
}

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Auth library for fetching ID tokens
const auth = new GoogleAuth();
let idTokenClient;

async function getAuthenticatedClient() {
    // Skip authentication for local development
    if (DEV_MODE) {
        console.log('Skipping authentication for local development');
        return null;
    }

    if (!idTokenClient) {
        // Extract the hostname from the URL to use as audience
        const audienceUrl = new URL(ACTUAL_BACKEND_URL).origin;
        console.log(`Fetching ID token client for target audience: ${audienceUrl}`);
        try {
            idTokenClient = await auth.getIdTokenClient(audienceUrl);
            console.log('Successfully created ID token client.');
        } catch (error) {
            console.error('Failed to create ID token client:', error);
            throw error;
        }
    }
    return idTokenClient;
}

// Special handler for Google Auth URL in development mode
app.get('/api/auth/google/url', (req, res) => {
    if (DEV_MODE) {
        console.log('DEV MODE: Returning mock Google auth URL');
        // Return mock auth URL that points back to our callback
        return res.json({
            success: true,
            auth_url: `http://localhost:3005/auth/google/callback.html?code=dev_mode_mock_code&state=dev_state`
        });
    } else {
        // Normal proxy behavior in production
        proxyRequest(req, res);
    }
});

// Special handler for Google Auth callback in development mode
app.get('/api/auth/google/callback', (req, res) => {
    if (DEV_MODE) {
        console.log('DEV MODE: Returning mock auth success');
        // Return mock successful authentication
        return res.json({
            success: true,
            user_info: {
                user_id: 1,
                email: "dev@example.com",
                name: "Development User",
                api_key: "DEV_API_KEY_1234567890"
            }
        });
    } else {
        // Normal proxy behavior in production
        proxyRequest(req, res);
    }
});

// Proxy API Routes
app.all('/api/*', async (req, res) => {
    // If this is one of our special handled routes in dev mode, skip the proxy
    if (DEV_MODE && 
        (req.path === '/api/auth/google/url' || req.path === '/api/auth/google/callback')) {
        return; // Already handled by special routes above
    }
    
    await proxyRequest(req, res);
});

async function proxyRequest(req, res) {
    const targetPath = req.originalUrl;
    const targetUrl = `${ACTUAL_BACKEND_URL}${targetPath}`;
    console.log(`Proxying request: ${req.method} ${targetPath} -> ${targetUrl}`);

    try {
        let headers = {};
        
        // Skip auth for local development
        if (DEV_MODE) {
            console.log('Using direct connection for local development');
        } else {
            try {
                const client = await getAuthenticatedClient();
                // Use the hostname for the token audience
                const audienceUrl = new URL(ACTUAL_BACKEND_URL).origin;
                const idToken = await client.idTokenProvider.fetchIdToken(audienceUrl);
                console.log(`Got ID token for ${audienceUrl} (length: ${idToken.length})`);
                headers['Authorization'] = `Bearer ${idToken}`;
            } catch (error) {
                console.error(`Error getting authentication token: ${error.message}`);
                // Continue without authentication in DEV_MODE
                if (!DEV_MODE) {
                    return res.status(500).json({ 
                        error: 'Authentication Error', 
                        message: 'Failed to get authentication token.'
                    });
                }
            }
        }

        // Forward relevant headers from original request (optional, adjust as needed)
        if (req.headers['content-type']) {
            headers['Content-Type'] = req.headers['content-type'];
        }

        console.log(`Request headers being sent to backend:`, headers);

        const backendResponse = await axios({
            method: req.method,
            url: targetUrl,
            headers: headers,
            data: req.body,
            validateStatus: status => true // Accept all status codes for debugging
        });

        console.log(`Backend response status for ${targetPath}: ${backendResponse.status}`);
        // Log the actual data/body received with the 400/error response
        if (backendResponse.status >= 400) {
            console.error(`ERROR - Backend response for ${targetPath} (status ${backendResponse.status}):`, 
                JSON.stringify(backendResponse.data, null, 2));
            console.error(`ERROR - Response headers:`, JSON.stringify(backendResponse.headers, null, 2));
        }
        res.status(backendResponse.status).json(backendResponse.data);

    } catch (error) {
        console.error(`Error proxying ${req.method} ${targetPath}:`, error.message);
        if (error.response) {
            console.error('Backend Error Response Status:', error.response.status);
            console.error('Backend Error Response Headers:', JSON.stringify(error.response.headers, null, 2));
            console.error('Backend Error Response Data:', JSON.stringify(error.response.data, null, 2));
            res.status(error.response.status).json(error.response.data);
        } else if (error.request) {
            console.error(`No response received from backend for ${targetPath}`);
            res.status(504).json({ error: 'Gateway Timeout', message: 'No response from backend service.' });
        } else {
            console.error(`Proxy request setup error for ${targetPath}:`, error.message);
            res.status(500).json({ error: 'Internal Server Error', message: 'Proxy configuration error.' });
        }
    }
}

// Function to inject config into HTML
const injectConfigAndServe = (filePath, res) => {
    fs.readFile(filePath, 'utf8', (err, htmlData) => {
        if (err) {
            console.error(`Error reading HTML file ${filePath}:`, err);
            return res.status(404).send('Page not found');
        }
        const modifiedHtml = htmlData.replace(
            '</head>',
            `<script>window.JEAN_CONFIG = { backendUrl: '${ACTUAL_BACKEND_URL}', devMode: ${DEV_MODE} };</script></head>`
        );
        res.send(modifiedHtml);
    });
};

// Specific routes for HTML files that need BACKEND_URL injected
app.get('/', (req, res) => {
    console.log('Serving / with injection');
    injectConfigAndServe(path.join(__dirname, 'public', 'index.html'), res);
});

app.get('/index.html', (req, res) => {
    console.log('Serving /index.html with injection');
    injectConfigAndServe(path.join(__dirname, 'public', 'index.html'), res);
});

app.get('/login.html', (req, res) => {
    console.log('Serving /login.html with injection');
    injectConfigAndServe(path.join(__dirname, 'public', 'login.html'), res);
});

app.get('/auth-success.html', (req, res) => {
    console.log('Serving /auth-success.html with injection');
    injectConfigAndServe(path.join(__dirname, 'public', 'auth-success.html'), res);
});

app.get('/auth/google/callback.html', (req, res) => {
    console.log('Serving /auth/google/callback.html with injection');
    injectConfigAndServe(path.join(__dirname, 'public', 'auth', 'google', 'callback.html'), res);
});

// This serves other static files directly (CSS, other JS, images, etc.)
// AND will serve any HTML files NOT caught by the routes above.
app.use(express.static(path.join(__dirname, 'public')));

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({ status: 'ok' });
});

// API endpoint to get MCP configuration
app.get('/api/mcp-config', (req, res) => {
  const apiKey = req.query.api_key || "DEV_API_KEY_1234567890";
  
  // Construct the MCP configuration
  const mcpConfig = {
    mcp_server_url: `${ACTUAL_BACKEND_URL}/mcp`,
    api_key: apiKey
  };

  res.json(mcpConfig);
});

// Start the server
app.listen(PORT, () => {
  console.log(`JEAN Frontend server really running on port ${PORT}`);
  console.log(`Backend URL for client: ${ACTUAL_BACKEND_URL}`);
}); 