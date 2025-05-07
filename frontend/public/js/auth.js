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
        AUTH_PROVIDER: 'authProvider' // New key to track login provider
    },

    // Initialize auth system
    init() {
        console.log("Initializing AuthManager...");
        
        // Check if session is valid or expired
        this.validateSession();
        
        // Check URL parameters for social auth immediately
        const params = new URLSearchParams(window.location.search);
        const authProvider = params.get('auth');
        if (authProvider) {
            console.log(`Auth provider detected in URL: ${authProvider}`);
            
            // For demo, bypass the intermediate page and login directly
            this.handleSocialAuthRedirect(authProvider);
            
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

    // Handle redirect from social auth
    handleSocialAuthRedirect(provider) {
        console.log(`Handling social auth redirect for provider: ${provider}`);
        
        // Show a notification
        if (typeof window.showNotification === 'function') {
            window.showNotification(`Signing in with ${provider}...`, 'info');
        }
        
        // This would normally verify the auth code with a backend API
        // For demo, we'll simulate a successful login
        const demoUsers = {
            'google': {
                userId: 'google-demo',
                apiKey: 'demo-api-key-google123',
                name: 'Google User',
                email: 'google@jeanmemory.ai',
                avatar: 'img/user-avatar.png',
                provider: 'google'
            },
            'github': {
                userId: 'github-demo',
                apiKey: 'demo-api-key-github123',
                name: 'GitHub User',
                email: 'github@jeanmemory.ai',
                avatar: '',
                provider: 'github'
            },
            'twitter': {
                userId: 'twitter-demo',
                apiKey: 'demo-api-key-twitter123',
                name: 'Twitter User',
                email: 'twitter@jeanmemory.ai',
                avatar: '',
                provider: 'twitter'
            }
        };
        
        if (demoUsers[provider]) {
            console.log(`Logging in user with ${provider} provider`);
            
            // Login with the demo user
            const success = this.login(demoUsers[provider]);
            
            if (success) {
                console.log(`Successfully logged in with ${provider}`);
                
                if (typeof window.showNotification === 'function') {
                    window.showNotification(`Successfully logged in with ${provider}`, 'success');
                }
                
                // Redirect to dashboard after a brief delay
                setTimeout(() => {
                    console.log('Redirecting to dashboard...');
                    window.location.href = 'dashboard.html';
                }, 500);
                
                return true;
            } else {
                console.error(`Failed to login with ${provider}`);
                
                if (typeof window.showNotification === 'function') {
                    window.showNotification(`Failed to login with ${provider}`, 'error');
                }
                
                return false;
            }
        } else {
            console.error(`Unknown provider: ${provider}`);
            
            if (typeof window.showNotification === 'function') {
                window.showNotification(`Unknown provider: ${provider}`, 'error');
            }
            
            return false;
        }
    },

    // Login user and store session data
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

    // Check if user is logged in
    isLoggedIn() {
        return localStorage.getItem(this.KEYS.IS_LOGGED_IN) === 'true';
    },

    // Get user data
    getUserData() {
        if (!this.isLoggedIn()) return null;
        
        return {
            userId: localStorage.getItem(this.KEYS.USER_ID),
            apiKey: localStorage.getItem(this.KEYS.API_KEY),
            name: localStorage.getItem(this.KEYS.USER_NAME),
            email: localStorage.getItem(this.KEYS.USER_EMAIL),
            avatar: localStorage.getItem(this.KEYS.AVATAR),
            provider: localStorage.getItem(this.KEYS.AUTH_PROVIDER) || 'email'
        };
    },

    // Validate session (check if expired)
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
            const userId = localStorage.getItem(this.KEYS.USER_ID);
            const apiKey = localStorage.getItem(this.KEYS.API_KEY);
            
            axios.defaults.headers.common['X-API-Key'] = apiKey;
            axios.defaults.headers.common['X-User-ID'] = userId;
        }
        
        return true;
    },

    // Update UI based on auth state
    updateUI() {
        if (!document.body) return; // Document not ready yet
        
        const isLoggedIn = this.isLoggedIn();
        const userInfo = isLoggedIn ? this.getUserData() : null;
        
        // Update user info display in header
        const userDisplay = document.getElementById('user-display');
        if (userDisplay) {
            if (isLoggedIn && userInfo) {
                let avatarHTML = '';
                
                if (userInfo.avatar) {
                    avatarHTML = `<img src="${userInfo.avatar}" alt="${userInfo.name}" class="user-avatar">`;
                } else {
                    // Use initials as avatar
                    const initials = userInfo.name.split(' ').map(n => n[0]).join('').toUpperCase();
                    avatarHTML = `<div class="user-initials">${initials}</div>`;
                }
                
                userDisplay.innerHTML = `
                    <div class="user-info">
                        ${avatarHTML}
                        <span class="user-name">${userInfo.name}</span>
                    </div>
                    <div class="dropdown-menu">
                        <a href="profile.html">Profile</a>
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

    // Check authentication and redirect if not logged in
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
    },

    // Get MCP config for user
    getMCPConfig() {
        if (!this.isLoggedIn()) return null;
        
        const userId = localStorage.getItem(this.KEYS.USER_ID);
        const apiKey = localStorage.getItem(this.KEYS.API_KEY);
        
        // Generate MCP config
        return {
            mcpServers: {
                "jean-memory": {
                    serverType: "HTTP",
                    serverUrl: window.location.origin,
                    headers: {
                        "X-API-Key": apiKey,
                        "X-User-ID": userId
                    }
                }
            }
        };
    }
};

// Initialize auth system
AuthManager.init();

// Export for use in other modules
window.AuthManager = AuthManager; 