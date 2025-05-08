// Authentication and session management
const AuthManager = {
    // Session storage keys
    KEYS: {
        USER_ID: 'userId',
        API_KEY: 'apiKey',
        USER_NAME: 'userName',
        USER_EMAIL: 'userEmail',
        AVATAR: 'userAvatar',
        IS_LOGGED_IN: 'isLoggedIn',
        SESSION_EXPIRY: 'sessionExpiry',
        AUTH_PROVIDER: 'authProvider',
        USER_INFO: 'userInfo' // Added for storing complete user info
    },

    // Initialize auth system
    init() {
        console.log("Initializing AuthManager...");
        
        // Check if session is valid or expired
        this.validateSession();
        
        // Check for auth-success from redirect
        const pathname = window.location.pathname;
        if (pathname.includes('auth-success')) {
            this.handleAuthSuccess();
        }
        
        // Check URL parameters for social auth
        const params = new URLSearchParams(window.location.search);
        const authProvider = params.get('provider');
        if (authProvider) {
            console.log(`Auth provider detected in URL: ${authProvider}`);
            
            // For Google auth, redirect to the backend OAuth endpoint
            if (authProvider === 'google') {
                this.startGoogleAuth();
            }
            
            // Clean up URL regardless of success
            window.history.replaceState({}, document.title, window.location.pathname);
        }
        
        // Update UI based on auth state
        this.updateUI();
        
        // Set up logout handlers
        document.addEventListener('DOMContentLoaded', () => {
            const logoutBtn = document.getElementById('logout-btn');
            if (logoutBtn) {
                logoutBtn.addEventListener('click', (e) => {
                    e.preventDefault();
                    this.logout();
                });
            }
        });
    },

    // Handle auth success from redirect
    handleAuthSuccess() {
        console.log("Auth success detected");
        
        const params = new URLSearchParams(window.location.search);
        const provider = params.get('provider');
        const completed = params.get('completed') === 'true';
        
        console.log("Auth Success params:", { provider, completed });
        console.log("Auth processed flag:", sessionStorage.getItem('auth_success_processed'));
        
        // Check if we're on the auth-success page after a completed OAuth flow
        if (completed || localStorage.getItem('auth_completed') === 'true') {
            console.log("Auth already completed, checking for user info");
            localStorage.removeItem('auth_completed');
            
            // For testing - if there's user info in localStorage, use it
            const userInfoString = localStorage.getItem('tempUserInfo');
            if (userInfoString) {
                try {
                    console.log("Found user info in localStorage, processing login");
                    const userInfo = JSON.parse(userInfoString);
                    this.storeUserInfo(userInfo);
                    localStorage.removeItem('tempUserInfo');
                    
                    // Redirect to dashboard or MCP config
                    if (typeof window.showNotification === 'function') {
                        window.showNotification(`Successfully logged in with ${provider}`, 'success');
                    }
                    
                    // Redirect to mcp-config after a short delay
                    console.log("Redirecting to MCP config page");
                    setTimeout(() => {
                        window.location.href = 'mcp-config.html';
                    }, 500);
                    
                    return true;
                } catch (e) {
                    console.error("Error parsing user info:", e);
                }
            } else {
                console.log("No user info found in localStorage");
            }
            
            // Check if we've already processed this auth success to prevent loops
            if (sessionStorage.getItem('auth_success_processed') === 'true') {
                console.log("Auth success already processed, redirecting to dashboard");
                // Clear the flag and redirect to dashboard
                sessionStorage.removeItem('auth_success_processed');
                window.location.href = 'dashboard.html';
                return true;
            }
        } else {
            console.log("Auth not yet completed or not on auth success page");
        }
        
        // If we've reached this point and we're on the auth-success page,
        // but there's no user info, redirect to login
        if (window.location.pathname.includes('auth-success')) {
            console.log("On auth-success page but missing user info, redirecting to login");
            window.location.href = 'login.html';
            return false;
        }
        
        return false;
    },

    // Start Google OAuth flow
    async startGoogleAuth() {
        // Check if we have an HTML-based callback handler
        const callbackHtmlExists = await fetch('/auth/google/callback.html', { method: 'HEAD' })
            .then(response => response.ok)
            .catch(() => false);
        
        console.log(`HTML-based callback available: ${callbackHtmlExists}`);
        
        // Try multiple backend URLs in order
        const possibleBackendUrls = [
            // First try the Docker service name
            'http://backend:8000',
            // Then try localhost (for local development outside Docker)
            'http://localhost:8000',
            // Finally try the origin (when frontend and backend are on same domain)
            window.location.origin
        ];

        // Generate a random user ID for initial auth
        const tempUserId = 'temp-' + Math.random().toString(36).substring(2, 15);
        
        // Try each URL in sequence until one works
        for (const backendUrl of possibleBackendUrls) {
            try {
                console.log(`Trying to connect to backend at: ${backendUrl}`);
                
                // Get the OAuth URL from the backend
                const response = await fetch(`${backendUrl}/api/auth/google/url?user_id=${tempUserId}`);
                
                if (response.ok) {
                    const data = await response.json();
                    if (data.auth_url) {
                        console.log("Successfully got auth URL, redirecting to Google OAuth");
                        // Redirect to Google OAuth
                        window.location.href = data.auth_url;
                        return; // Exit after successful redirect
                    } else {
                        console.warn("Auth URL not provided by backend, trying next URL");
                    }
                } else {
                    console.warn(`Backend at ${backendUrl} returned status: ${response.status}`);
                }
            } catch (error) {
                console.warn(`Failed to connect to ${backendUrl}: ${error.message}`);
                // Continue to the next URL
            }
        }
        
        // If we've tried all URLs and none worked, show an error
        console.error("Could not connect to any backend endpoint");
        if (typeof window.showNotification === 'function') {
            window.showNotification(`Failed to start Google authentication: Could not connect to backend server`, 'error');
        }
        
        // Fall back to demo login
        console.log("Falling back to demo login");
        this.login({
            userId: 'google-demo',
            apiKey: 'demo-api-key-google123',
            name: 'Google User',
            email: 'google@jeanmemory.ai',
            avatar: 'img/user-avatar.png',
            provider: 'google'
        });
    },

    // Store user info from social auth
    storeUserInfo(userInfo) {
        if (!userInfo) return false;
        
        const { user_id, email, name, picture, api_key } = userInfo;
        
        // Store data using all supported formats to ensure compatibility
        
        // Format 1: Complete userInfo object (for mcp-config.html)
        localStorage.setItem('userInfo', JSON.stringify(userInfo));
        
        // Format 2: AuthManager's internal format
        localStorage.setItem(this.KEYS.USER_INFO, JSON.stringify(userInfo));
        
        // Format 3: Individual fields for backward compatibility
        localStorage.setItem(this.KEYS.USER_ID, user_id);
        localStorage.setItem(this.KEYS.API_KEY, api_key);
        localStorage.setItem(this.KEYS.USER_NAME, name || 'User');
        localStorage.setItem(this.KEYS.USER_EMAIL, email || '');
        localStorage.setItem(this.KEYS.AVATAR, picture || '');
        localStorage.setItem(this.KEYS.IS_LOGGED_IN, 'true');
        localStorage.setItem(this.KEYS.AUTH_PROVIDER, 'google');
        
        // Format 4: Simplified fields (used by some pages)
        localStorage.setItem('userId', user_id);
        localStorage.setItem('apiKey', api_key);
        localStorage.setItem('userName', name || 'User');
        localStorage.setItem('userEmail', email || '');
        localStorage.setItem('userAvatar', picture || '');
        
        // Set session expiry (30 days from now)
        const expiryDate = new Date();
        expiryDate.setDate(expiryDate.getDate() + 30);
        localStorage.setItem(this.KEYS.SESSION_EXPIRY, expiryDate.toISOString());
        
        // Set up auth headers for axios
        if (window.axios) {
            axios.defaults.headers.common['X-API-Key'] = api_key;
            axios.defaults.headers.common['X-User-ID'] = user_id;
        }
        
        // Update UI
        this.updateUI();
        
        // Clear any temporary storage that might cause loops
        localStorage.removeItem('tempUserInfo');
        localStorage.removeItem('auth_completed');
        sessionStorage.removeItem('auth_success_processed');
        
        console.log('User info stored successfully in all formats', { user_id, name, email });
        return true;
    },

    // Use original login function for direct logins (not social auth)
    login(userData) {
        const { userId, apiKey, name, email, avatar, provider } = userData;
        
        // Set session expiry (30 days from now)
        const expiryDate = new Date();
        expiryDate.setDate(expiryDate.getDate() + 30);
        
        // Store in localStorage for persistence
        localStorage.setItem(this.KEYS.USER_ID, userId);
        localStorage.setItem(this.KEYS.API_KEY, apiKey);
        localStorage.setItem(this.KEYS.USER_NAME, name || 'User');
        localStorage.setItem(this.KEYS.USER_EMAIL, email || '');
        localStorage.setItem(this.KEYS.AVATAR, avatar || '');
        localStorage.setItem(this.KEYS.IS_LOGGED_IN, 'true');
        localStorage.setItem(this.KEYS.SESSION_EXPIRY, expiryDate.toISOString());
        if (provider) {
            localStorage.setItem(this.KEYS.AUTH_PROVIDER, provider);
        }
        
        // Set up auth headers for axios
        if (window.axios) {
            axios.defaults.headers.common['X-API-Key'] = apiKey;
            axios.defaults.headers.common['X-User-ID'] = userId;
        }
        
        // Update UI
        this.updateUI();
        
        console.log('Login successful', { userId, name, email });
        return true;
    },

    // Logout user and clear session data
    logout() {
        // Store the current auth provider (for potential re-login)
        const provider = localStorage.getItem(this.KEYS.AUTH_PROVIDER);
        
        // Clear localStorage
        Object.values(this.KEYS).forEach(key => localStorage.removeItem(key));
        
        // Clear auth headers
        if (window.axios) {
            delete axios.defaults.headers.common['X-API-Key'];
            delete axios.defaults.headers.common['X-User-ID'];
        }
        
        // Redirect to login page
        window.location.href = `/login.html${provider ? '?last_provider=' + provider : ''}`;
    },

    // Get user data for MCP config
    getMCPConfig() {
        if (!this.isLoggedIn()) return null;
        
        // Get user info from localStorage
        const userInfo = JSON.parse(localStorage.getItem(this.KEYS.USER_INFO) || '{}');
        const userId = userInfo.user_id || localStorage.getItem(this.KEYS.USER_ID);
        const apiKey = userInfo.api_key || localStorage.getItem(this.KEYS.API_KEY);
        
        if (!userId || !apiKey) {
            console.error("Missing user ID or API key for MCP config");
            return null;
        }
        
        // Get base URL from environment or use location origin
        const baseUrl = (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') 
            ? 'http://localhost:8000' 
            : window.location.origin;
        
        // Generate MCP config
        return {
            mcpServers: {
                "jean-memory": {
                    serverType: "HTTP",
                    serverUrl: baseUrl,
                    headers: {
                        "X-API-Key": apiKey,
                        "X-User-ID": userId
                    }
                }
            }
        };
    },

    // The rest of the methods remain unchanged
    isLoggedIn() {
        return localStorage.getItem(this.KEYS.IS_LOGGED_IN) === 'true';
    },

    getUserData() {
        if (!this.isLoggedIn()) return null;
        
        // First try to get complete user info
        const userInfoJson = localStorage.getItem(this.KEYS.USER_INFO);
        if (userInfoJson) {
            try {
                return JSON.parse(userInfoJson);
            } catch (e) {
                console.error("Error parsing user info:", e);
            }
        }
        
        // Fallback to individual fields
        return {
            userId: localStorage.getItem(this.KEYS.USER_ID),
            apiKey: localStorage.getItem(this.KEYS.API_KEY),
            name: localStorage.getItem(this.KEYS.USER_NAME),
            email: localStorage.getItem(this.KEYS.USER_EMAIL),
            avatar: localStorage.getItem(this.KEYS.AVATAR),
            provider: localStorage.getItem(this.KEYS.AUTH_PROVIDER) || 'email'
        };
    },

    validateSession() {
        if (!this.isLoggedIn()) return false;
        
        const expiryStr = localStorage.getItem(this.KEYS.SESSION_EXPIRY);
        if (!expiryStr) return false;
        
        const expiryDate = new Date(expiryStr);
        const now = new Date();
        
        // If session expired, logout
        if (now > expiryDate) {
            console.log("Session expired, logging out");
            this.logout();
            return false;
        }
        
        // Extend session by another 30 days if we're within 5 days of expiry
        const fiveDaysMs = 5 * 24 * 60 * 60 * 1000;
        if (expiryDate.getTime() - now.getTime() < fiveDaysMs) {
            console.log("Extending session");
            const newExpiry = new Date();
            newExpiry.setDate(newExpiry.getDate() + 30);
            localStorage.setItem(this.KEYS.SESSION_EXPIRY, newExpiry.toISOString());
        }
        
        // Set up auth headers for axios if they don't exist
        if (window.axios) {
            const userInfo = JSON.parse(localStorage.getItem(this.KEYS.USER_INFO) || '{}');
            const userId = userInfo.user_id || localStorage.getItem(this.KEYS.USER_ID);
            const apiKey = userInfo.api_key || localStorage.getItem(this.KEYS.API_KEY);
            
            axios.defaults.headers.common['X-API-Key'] = apiKey;
            axios.defaults.headers.common['X-User-ID'] = userId;
        }
        
        return true;
    },

    updateUI() {
        if (!document.body) return; // Document not ready yet
        
        const isLoggedIn = this.isLoggedIn();
        const userInfo = isLoggedIn ? this.getUserData() : null;
        
        // Update user info display in header
        const userDisplay = document.getElementById('user-display');
        if (userDisplay) {
            if (isLoggedIn && userInfo) {
                let avatarHTML = '';
                const userName = userInfo.name || userInfo.userName || 'User';
                
                // Get avatar from userInfo or fall back to previous keys
                const avatar = userInfo.picture || userInfo.avatar;
                
                if (avatar) {
                    avatarHTML = `<img src="${avatar}" alt="${userName}" class="user-avatar">`;
                } else {
                    // Use initials as avatar
                    const initials = userName.split(' ').map(n => n[0]).join('').toUpperCase();
                    avatarHTML = `<div class="user-initials">${initials}</div>`;
                }
                
                userDisplay.innerHTML = `
                    <div class="user-info">
                        ${avatarHTML}
                        <span class="user-name">${userName}</span>
                    </div>
                    <div class="dropdown-menu">
                        <a href="profile.html">Profile</a>
                        <a href="mcp-config.html">MCP Config</a>
                        <a href="settings.html">Settings</a>
                        <a href="#" id="logout-btn">Logout</a>
                    </div>
                `;
                
                // Add event listener for dropdown
                const userInfoElement = userDisplay.querySelector('.user-info');
                if (userInfoElement) {
                    userInfoElement.addEventListener('click', () => {
                        userDisplay.classList.toggle('active');
                    });
                    
                    // Close dropdown when clicking elsewhere
                    document.addEventListener('click', (event) => {
                        if (!userDisplay.contains(event.target)) {
                            userDisplay.classList.remove('active');
                        }
                    });
                }
                
                // Set up logout handler
                const logoutBtn = userDisplay.querySelector('#logout-btn');
                if (logoutBtn) {
                    logoutBtn.addEventListener('click', (e) => {
                        e.preventDefault();
                        this.logout();
                    });
                }
            } else {
                userDisplay.innerHTML = `<a href="login.html" class="login-btn">Login</a>`;
            }
        }
    },

    requireAuth() {
        if (!this.isLoggedIn()) {
            // Save current page for redirect after login
            const currentPage = window.location.pathname;
            sessionStorage.setItem('redirectAfterLogin', currentPage);
            
            // Redirect to login
            window.location.href = '/login.html';
            return false;
        }
        
        return true;
    }
};

// Initialize auth system
AuthManager.init();

// Export for use in other modules
window.AuthManager = AuthManager; 