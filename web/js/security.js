/**
 * Lazarus Protocol Security Module
 * Provides comprehensive security features for the dashboard
 * Version: 1.0.0
 */

class LazarusSecurity {
    constructor(config = {}) {
        this.config = {
            apiBase: config.apiBase || window.location.origin,
            sessionTimeout: config.sessionTimeout || 30 * 60 * 1000, // 30 minutes
            tokenRefreshThreshold: config.tokenRefreshThreshold || 5 * 60 * 1000, // 5 minutes
            ...config
        };
        
        this.authToken = null;
        this.refreshToken = null;
        this.csrfToken = null;
        this.sessionExpiry = null;
        this.lastActivity = Date.now();
        this.activityCheckInterval = null;
        this.tokenRefreshInterval = null;
        
        // Server-provided encryption key management
        this.sessionKeyId = null;
        this.encryptionKey = null;
        this.keyExpiry = null;
        
        this.initialize();
    }
    
    /**
     * Initialize security module
     */
    async initialize() {
        this.loadTokens();
        this.startActivityMonitoring();
        this.startTokenRefresh();
        this.enforceHTTPS();
        
        // Initialize server-provided encryption key
        await this.initializeServerEncryptionKey();
    }
    
    /**
     * Initialize server-provided encryption key
     */
    async initializeServerEncryptionKey() {
        try {
            const sessionId = this.generateSessionId();
            const userAgent = navigator.userAgent;
            
            const response = await fetch(`${this.config.apiBase}/api/session/key`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${this.authToken || ''}`
                },
                body: JSON.stringify({
                    session_id: sessionId,
                    user_agent: userAgent
                })
            });
            
            if (response.ok) {
                const data = await response.json();
                this.sessionKeyId = data.key_id;
                this.encryptionKey = data.key;
                this.keyExpiry = new Date(data.expires_at);
                
                // Store key metadata (not the actual key) for session tracking
                localStorage.setItem('lazarus_session_key_id', this.sessionKeyId);
                localStorage.setItem('lazarus_key_expiry', this.keyExpiry.toISOString());
                
                console.log('Server-provided encryption key initialized');
            } else {
                console.warn('Failed to get server encryption key, using fallback');
                this.encryptionKey = this.generateFallbackKey();
            }
        } catch (error) {
            console.error('Error initializing server encryption key:', error);
            this.encryptionKey = this.generateFallbackKey();
        }
    }
    
    /**
     * Generate unique session ID
     */
    generateSessionId() {
        const timestamp = Date.now().toString(36);
        const randomPart = Array.from(crypto.getRandomValues(new Uint8Array(16)))
            .map(b => b.toString(16).padStart(2, '0'))
            .join('');
        return `${timestamp}-${randomPart}`;
    }
    
    /**
     * Generate fallback encryption key (only used if server key fails)
     */
    generateFallbackKey() {
        const array = new Uint8Array(32);
        crypto.getRandomValues(array);
        return Array.from(array, byte => byte.toString(16).padStart(2, '0')).join('');
    }
    
    /**
     * Enforce HTTPS connection
     */
    enforceHTTPS() {
        if (window.location.protocol === 'http:' && window.location.hostname !== 'localhost') {
            console.warn('Insecure connection detected. Redirecting to HTTPS...');
            window.location.href = window.location.href.replace('http:', 'https:');
        }
    }
    
    /**
     * Load tokens from localStorage
     */
    loadTokens() {
        try {
            this.authToken = localStorage.getItem('lazarus_auth_token');
            this.refreshToken = localStorage.getItem('lazarus_refresh_token');
            this.csrfToken = localStorage.getItem('lazarus_csrf_token');
            this.sessionExpiry = parseInt(localStorage.getItem('lazarus_session_expiry') || '0');
        } catch (error) {
            console.error('Failed to load tokens:', error);
            this.clearTokens();
        }
    }
    
    /**
     * Save tokens to localStorage
     */
    saveTokens(authToken, refreshToken, csrfToken, expiresIn) {
        try {
            localStorage.setItem('lazarus_auth_token', authToken);
            localStorage.setItem('lazarus_refresh_token', refreshToken);
            localStorage.setItem('lazarus_csrf_token', csrfToken);
            localStorage.setItem('lazarus_session_expiry', (Date.now() + expiresIn).toString());
            
            this.authToken = authToken;
            this.refreshToken = refreshToken;
            this.csrfToken = csrfToken;
            this.sessionExpiry = Date.now() + expiresIn;
        } catch (error) {
            console.error('Failed to save tokens:', error);
        }
    }
    
    /**
     * Clear all tokens
     */
    clearTokens() {
        localStorage.removeItem('lazarus_auth_token');
        localStorage.removeItem('lazarus_refresh_token');
        localStorage.removeItem('lazarus_csrf_token');
        localStorage.removeItem('lazarus_session_expiry');
        
        this.authToken = null;
        this.refreshToken = null;
        this.csrfToken = null;
        this.sessionExpiry = null;
    }
    
    /**
     * Check if session is valid
     */
    isSessionValid() {
        if (!this.authToken || !this.sessionExpiry) {
            return false;
        }
        
        return Date.now() < this.sessionExpiry;
    }
    
    /**
     * Start activity monitoring
     */
    startActivityMonitoring() {
        // Update activity on user interaction
        const events = ['click', 'keydown', 'scroll', 'touchstart'];
        events.forEach(event => {
            document.addEventListener(event, () => this.updateActivity());
        });
        
        // Check for session timeout
        this.activityCheckInterval = setInterval(() => {
            const inactiveTime = Date.now() - this.lastActivity;
            if (inactiveTime > this.config.sessionTimeout) {
                this.logout('Session expired due to inactivity');
            }
        }, 60000); // Check every minute
    }
    
    /**
     * Update last activity timestamp
     */
    updateActivity() {
        this.lastActivity = Date.now();
    }
    
    /**
     * Start automatic token refresh
     */
    startTokenRefresh() {
        this.tokenRefreshInterval = setInterval(async () => {
            if (this.isSessionValid()) {
                const timeUntilExpiry = this.sessionExpiry - Date.now();
                if (timeUntilExpiry < this.config.tokenRefreshThreshold) {
                    await this.refreshTokens();
                }
            }
        }, 60000); // Check every minute
    }
    
    /**
     * Authenticate with credentials
     */
    async authenticate(credentials) {
        try {
            const response = await this.fetchWithAuth('/auth/login', {
                method: 'POST',
                body: JSON.stringify(credentials)
            });
            
            if (!response.ok) {
                throw new Error('Authentication failed');
            }
            
            const data = await response.json();
            this.saveTokens(
                data.access_token,
                data.refresh_token,
                data.csrf_token,
                data.expires_in * 1000
            );
            
            return { success: true, data };
        } catch (error) {
            console.error('Authentication error:', error);
            return { success: false, error: error.message };
        }
    }
    
    /**
     * Refresh tokens
     */
    async refreshTokens() {
        if (!this.refreshToken) {
            return { success: false, error: 'No refresh token available' };
        }
        
        try {
            const response = await this.fetchWithAuth('/auth/refresh', {
                method: 'POST',
                body: JSON.stringify({ refresh_token: this.refreshToken })
            });
            
            if (!response.ok) {
                throw new Error('Token refresh failed');
            }
            
            const data = await response.json();
            this.saveTokens(
                data.access_token,
                data.refresh_token || this.refreshToken,
                data.csrf_token,
                data.expires_in * 1000
            );
            
            return { success: true, data };
        } catch (error) {
            console.error('Token refresh error:', error);
            this.logout('Session expired');
            return { success: false, error: error.message };
        }
    }
    
    /**
     * Logout
     */
    async logout(reason = 'User logged out') {
        try {
            // Notify server
            if (this.authToken) {
                await this.fetchWithAuth('/auth/logout', {
                    method: 'POST'
                });
            }
        } catch (error) {
            console.error('Logout error:', error);
        } finally {
            this.clearTokens();
            this.stopMonitoring();
            
            // Redirect to login
            if (window.location.pathname !== '/login') {
                window.location.href = '/login?reason=' + encodeURIComponent(reason);
            }
        }
    }
    
    /**
     * Stop monitoring intervals
     */
    stopMonitoring() {
        if (this.activityCheckInterval) {
            clearInterval(this.activityCheckInterval);
        }
        if (this.tokenRefreshInterval) {
            clearInterval(this.tokenRefreshInterval);
        }
    }
    
    /**
     * Make authenticated fetch request
     */
    async fetchWithAuth(url, options = {}) {
        // Ensure session is valid
        if (!this.isSessionValid()) {
            await this.logout('Session expired');
            throw new Error('Session expired');
        }
        
        // Prepare headers
        const headers = {
            'Content-Type': 'application/json',
            ...options.headers
        };
        
        // Add authentication token
        if (this.authToken) {
            headers['Authorization'] = `Bearer ${this.authToken}`;
        }
        
        // Add CSRF token for POST/PUT/DELETE requests
        if (['POST', 'PUT', 'DELETE', 'PATCH'].includes(options.method)) {
            if (this.csrfToken) {
                headers['X-CSRF-Token'] = this.csrfToken;
            }
        }
        
        // Prepare request
        const requestOptions = {
            ...options,
            headers
        };
        
        // Add timeout
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), options.timeout || 30000);
        requestOptions.signal = controller.signal;
        
        try {
            const fullUrl = url.startsWith('http') ? url : `${this.config.apiBase}${url}`;
            const response = await fetch(fullUrl, requestOptions);
            clearTimeout(timeoutId);
            
            // Handle 401 Unauthorized
            if (response.status === 401) {
                const refreshResult = await this.refreshTokens();
                if (refreshResult.success) {
                    // Retry request with new token
                    return this.fetchWithAuth(url, options);
                } else {
                    await this.logout('Authentication failed');
                    throw new Error('Authentication failed');
                }
            }
            
            return response;
        } catch (error) {
            clearTimeout(timeoutId);
            
            if (error.name === 'AbortError') {
                throw new Error('Request timeout');
            }
            
            throw error;
        }
    }
    
    /**
     * Encrypt data for localStorage using server-provided key
     */
    async encryptData(data) {
        try {
            // Ensure we have a valid encryption key
            if (!this.encryptionKey) {
                await this.initializeServerEncryptionKey();
            }
            
            // Check if key is expired and needs rotation
            if (this.keyExpiry && new Date() > this.keyExpiry) {
                await this.rotateEncryptionKey();
            }
            
            const jsonString = JSON.stringify(data);
            const encoder = new TextEncoder();
            const dataBuffer = encoder.encode(jsonString);
            
            // Generate key from server-provided encryption key using PBKDF2
            const keyMaterial = await crypto.subtle.importKey(
                'raw',
                new TextEncoder().encode(this.encryptionKey),
                'PBKDF2',
                false,
                ['deriveKey']
            );
            
            const key = await crypto.subtle.deriveKey(
                {
                    name: 'PBKDF2',
                    salt: new TextEncoder().encode('lazarus-server-key'),
                    iterations: 100000,
                    hash: 'SHA-256'
                },
                keyMaterial,
                { name: 'AES-GCM', length: 256 },
                false,
                ['encrypt']
            );
            
            const iv = crypto.getRandomValues(new Uint8Array(12));
            const encrypted = await crypto.subtle.encrypt(
                { name: 'AES-GCM', iv },
                key,
                dataBuffer
            );
            
            // Combine IV and encrypted data
            const combined = new Uint8Array(iv.length + encrypted.byteLength);
            combined.set(iv);
            combined.set(new Uint8Array(encrypted), iv.length);
            
            // Convert to base64
            return btoa(String.fromCharCode(...combined));
        } catch (error) {
            console.error('Encryption error:', error);
            throw new Error('Failed to encrypt data');
        }
    }
    
    /**
     * Decrypt data from localStorage using server-provided key
     */
    async decryptData(encryptedData) {
        try {
            // Ensure we have a valid encryption key
            if (!this.encryptionKey) {
                await this.initializeServerEncryptionKey();
            }
            
            // Convert from base64
            const combined = new Uint8Array(
                atob(encryptedData).split('').map(c => c.charCodeAt(0))
            );
            
            // Extract IV and encrypted data
            const iv = combined.slice(0, 12);
            const encrypted = combined.slice(12);
            
            // Generate key from server-provided encryption key using PBKDF2
            const keyMaterial = await crypto.subtle.importKey(
                'raw',
                new TextEncoder().encode(this.encryptionKey),
                'PBKDF2',
                false,
                ['deriveKey']
            );
            
            const key = await crypto.subtle.deriveKey(
                {
                    name: 'PBKDF2',
                    salt: new TextEncoder().encode('lazarus-server-key'),
                    iterations: 100000,
                    hash: 'SHA-256'
                },
                keyMaterial,
                { name: 'AES-GCM', length: 256 },
                false,
                ['decrypt']
            );
            
            const decrypted = await crypto.subtle.decrypt(
                { name: 'AES-GCM', iv },
                key,
                encrypted
            );
            
            const decoder = new TextDecoder();
            return JSON.parse(decoder.decode(decrypted));
        } catch (error) {
            console.error('Decryption error:', error);
            throw new Error('Failed to decrypt data');
        }
    }
    
    /**
     * Rotate encryption key for enhanced security
     */
    async rotateEncryptionKey() {
        try {
            if (!this.sessionKeyId) {
                console.warn('No session key ID to rotate');
                return;
            }
            
            const response = await fetch(`${this.config.apiBase}/api/session/key/rotate`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${this.authToken || ''}`
                },
                body: JSON.stringify({
                    key_id: this.sessionKeyId
                })
            });
            
            if (response.ok) {
                const data = await response.json();
                this.sessionKeyId = data.key_id;
                this.encryptionKey = data.key;
                this.keyExpiry = new Date(data.expires_at);
                
                // Update stored metadata
                localStorage.setItem('lazarus_session_key_id', this.sessionKeyId);
                localStorage.setItem('lazarus_key_expiry', this.keyExpiry.toISOString());
                
                console.log('Encryption key rotated successfully');
            } else {
                console.warn('Failed to rotate encryption key');
            }
        } catch (error) {
            console.error('Error rotating encryption key:', error);
        }
    }
    
    /**
     * Sanitize HTML to prevent XSS
     */
    sanitizeHTML(html) {
        if (typeof html !== 'string') {
            return '';
        }
        
        // Basic HTML sanitization
        const temp = document.createElement('div');
        temp.textContent = html;
        return temp.innerHTML;
    }
    
    /**
     * Validate file path to prevent path traversal
     */
    validateFilePath(filePath) {
        if (!filePath || typeof filePath !== 'string') {
            throw new Error('File path is required');
        }
        
        // Prevent path traversal
        if (filePath.includes('..') || filePath.includes('~') || filePath.includes('/../')) {
            throw new Error('Invalid file path: path traversal detected');
        }
        
        // Restrict to allowed directories
        const allowedDirs = ['/documents/', '/uploads/', '/secure/', '/data/'];
        const isAllowed = allowedDirs.some(dir => filePath.startsWith(dir));
        
        if (!isAllowed) {
            throw new Error('File path not in allowed directory');
        }
        
        // Validate file extension
        const allowedExtensions = ['.txt', '.pdf', '.doc', '.docx', '.json', '.md'];
        const hasAllowedExtension = allowedExtensions.some(ext => 
            filePath.toLowerCase().endsWith(ext)
        );
        
        if (!hasAllowedExtension) {
            throw new Error('File type not allowed');
        }
        
        // Check path length
        if (filePath.length > 255) {
            throw new Error('File path too long');
        }
        
        return true;
    }
    
    /**
     * Validate input data
     */
    validateInput(type, value) {
        const validators = {
            freezeDays: (val) => {
                const num = parseInt(val);
                if (isNaN(num) || num < 1 || num > 365) {
                    throw new Error('Days must be between 1 and 365');
                }
                return num;
            },
            
            filePath: (val) => {
                return this.validateFilePath(val);
            },
            
            documentType: (val) => {
                const validTypes = ['WALLET', 'PASSWORD', 'INSTRUCTION', 'LEGAL', 'OTHER'];
                if (!validTypes.includes(val)) {
                    throw new Error('Invalid document type');
                }
                return val;
            },
            
            email: (val) => {
                const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
                if (!emailRegex.test(val)) {
                    throw new Error('Invalid email format');
                }
                return val;
            },
            
            phoneNumber: (val) => {
                const phoneRegex = /^\+?[\d\s-()]+$/;
                if (!phoneRegex.test(val)) {
                    throw new Error('Invalid phone number format');
                }
                return val;
            }
        };
        
        const validator = validators[type];
        if (!validator) {
            throw new Error(`No validator for type: ${type}`);
        }
        
        return validator(value);
    }
    
    /**
     * Get security headers for HTML
     */
    getSecurityHeaders() {
        return {
            'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self'; connect-src 'self' https://api.sendgrid.com; frame-ancestors 'none'; base-uri 'self'; form-action 'self';",
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
            'Strict-Transport-Security': 'max-age=31536000; includeSubDomains; preload',
            'Referrer-Policy': 'strict-origin-when-cross-origin',
            'Permissions-Policy': 'camera=(), microphone=(), geolocation=(), payment=()'
        };
    }
    
    /**
     * Generate CSRF token
     */
    async generateCSRFToken() {
        const array = new Uint8Array(32);
        crypto.getRandomValues(array);
        return Array.from(array, byte => byte.toString(16).padStart(2, '0')).join('');
    }
    
    /**
     * Get current CSRF token
     */
    getCSRFToken() {
        return this.csrfToken;
    }
    
    /**
     * Check if user is authenticated
     */
    isAuthenticated() {
        return this.isSessionValid() && !!this.authToken;
    }
    
    /**
     * Get authentication token
     */
    getAuthToken() {
        return this.authToken;
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = LazarusSecurity;
}