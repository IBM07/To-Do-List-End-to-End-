/**
 * ===========================================
 * AuraTask - API Service Module
 * ===========================================
 * Handles all HTTP requests to the backend
 */

const API_BASE_URL = 'http://localhost:8000/api';

/**
 * API Service Class
 * Manages authentication headers and CRUD operations
 */
class ApiService {
    constructor() {
        this.baseUrl = API_BASE_URL;
        this.token = localStorage.getItem('auratask_token');
    }

    // ===========================================
    // Token Management
    // ===========================================

    /**
     * Set the authentication token
     */
    setToken(token) {
        this.token = token;
        localStorage.setItem('auratask_token', token);
    }

    /**
     * Clear the authentication token
     */
    clearToken() {
        this.token = null;
        localStorage.removeItem('auratask_token');
    }

    /**
     * Check if user is authenticated
     */
    isAuthenticated() {
        return !!this.token;
    }

    // ===========================================
    // HTTP Request Methods
    // ===========================================

    /**
     * Build headers for requests
     */
    getHeaders(includeAuth = true) {
        const headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        };

        if (includeAuth && this.token) {
            headers['Authorization'] = `Bearer ${this.token}`;
        }

        return headers;
    }

    /**
     * Handle API response
     */
    async handleResponse(response) {
        // Handle 401 Unauthorized - redirect to login
        if (response.status === 401) {
            this.clearToken();
            window.dispatchEvent(new CustomEvent('auth:logout'));
            throw new Error('Session expired. Please login again.');
        }

        // Parse JSON response
        const data = await response.json().catch(() => ({}));

        if (!response.ok) {
            const errorMessage = data.detail || `Request failed with status ${response.status}`;
            throw new Error(errorMessage);
        }

        return data;
    }

    /**
     * Generic fetch wrapper with error handling
     */
    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;

        const config = {
            headers: this.getHeaders(options.auth !== false),
            ...options,
        };

        try {
            const response = await fetch(url, config);
            return await this.handleResponse(response);
        } catch (error) {
            console.error(`API Error [${options.method || 'GET'}] ${endpoint}:`, error);
            throw error;
        }
    }

    /**
     * GET request
     */
    async get(endpoint, params = {}) {
        const queryString = new URLSearchParams(params).toString();
        const url = queryString ? `${endpoint}?${queryString}` : endpoint;
        return this.request(url, { method: 'GET' });
    }

    /**
     * POST request
     */
    async post(endpoint, data, options = {}) {
        return this.request(endpoint, {
            method: 'POST',
            body: JSON.stringify(data),
            ...options,
        });
    }

    /**
     * PUT request
     */
    async put(endpoint, data) {
        return this.request(endpoint, {
            method: 'PUT',
            body: JSON.stringify(data),
        });
    }

    /**
     * PATCH request
     */
    async patch(endpoint, data) {
        return this.request(endpoint, {
            method: 'PATCH',
            body: JSON.stringify(data),
        });
    }

    /**
     * DELETE request
     */
    async delete(endpoint) {
        return this.request(endpoint, { method: 'DELETE' });
    }

    // ===========================================
    // Authentication Endpoints
    // ===========================================

    /**
     * Register a new user
     */
    async register(email, password, timezone = 'UTC') {
        const data = await this.post('/auth/register', {
            email,
            password,
            timezone,
        }, { auth: false });

        return data;
    }

    /**
     * Login and get token
     */
    async login(email, password) {
        const data = await this.post('/auth/login/json', {
            email,
            password,
        }, { auth: false });

        if (data.access_token) {
            this.setToken(data.access_token);
        }

        return data;
    }

    /**
     * Logout
     */
    logout() {
        this.clearToken();
        window.dispatchEvent(new CustomEvent('auth:logout'));
    }

    /**
     * Get current user profile
     */
    async getMe() {
        return this.get('/auth/me');
    }

    /**
     * Refresh token
     */
    async refreshToken() {
        const data = await this.post('/auth/refresh', {});
        if (data.access_token) {
            this.setToken(data.access_token);
        }
        return data;
    }

    // ===========================================
    // Task Endpoints
    // ===========================================

    /**
     * Get all tasks with optional filters
     */
    async getTasks(params = {}) {
        return this.get('/tasks/', params);
    }

    /**
     * Get a single task by ID
     */
    async getTask(taskId) {
        return this.get(`/tasks/${taskId}`);
    }

    /**
     * Create a new task (supports NLP input)
     */
    async createTask(taskData) {
        return this.post('/tasks/', taskData);
    }

    /**
     * Update a task
     */
    async updateTask(taskId, updates) {
        return this.put(`/tasks/${taskId}`, updates);
    }

    /**
     * Complete a task
     */
    async completeTask(taskId) {
        return this.post(`/tasks/${taskId}/complete`, {});
    }

    /**
     * Snooze a task (default 60 minutes)
     */
    async snoozeTask(taskId, minutes = 60) {
        return this.post(`/tasks/${taskId}/snooze`, { snooze_minutes: minutes });
    }

    /**
     * Delete a task
     */
    async deleteTask(taskId) {
        return this.delete(`/tasks/${taskId}`);
    }

    // ===========================================
    // Notification Endpoints
    // ===========================================

    /**
     * Get notification settings
     */
    async getNotificationSettings() {
        return this.get('/notifications/settings');
    }

    /**
     * Update notification settings
     */
    async updateNotificationSettings(settings) {
        return this.put('/notifications/settings', settings);
    }

    /**
     * Test notification channel
     */
    async testNotification(channel, message = null) {
        return this.post('/notifications/test', { channel, message });
    }
}

// Create singleton instance
const api = new ApiService();

export { api, ApiService };
export default api;
