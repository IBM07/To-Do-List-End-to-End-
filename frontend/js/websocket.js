/**
 * ===========================================
 * AuraTask - WebSocket Client Module
 * ===========================================
 * Real-time connection for live task updates
 */

const WS_BASE_URL = 'ws://localhost:8000/ws/tasks';

/**
 * WebSocket Manager Class
 * Handles real-time communication with the server
 */
class WebSocketManager {
    constructor() {
        this.socket = null;
        this.userId = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 3000;
        this.listeners = new Map();
    }

    // ===========================================
    // Connection Management
    // ===========================================

    /**
     * Connect to WebSocket server
     */
    connect(userId) {
        if (this.socket?.readyState === WebSocket.OPEN) {
            console.log('WebSocket already connected');
            return;
        }

        this.userId = userId;
        const url = `${WS_BASE_URL}/${userId}`;

        console.log(`🔌 Connecting to WebSocket: ${url}`);

        this.socket = new WebSocket(url);

        this.socket.onopen = () => this.handleOpen();
        this.socket.onmessage = (event) => this.handleMessage(event);
        this.socket.onclose = (event) => this.handleClose(event);
        this.socket.onerror = (error) => this.handleError(error);
    }

    /**
     * Disconnect from WebSocket server
     */
    disconnect() {
        if (this.socket) {
            this.socket.close(1000, 'User logout');
            this.socket = null;
        }
        this.userId = null;
        this.reconnectAttempts = 0;
    }

    /**
     * Check if connected
     */
    isConnected() {
        return this.socket?.readyState === WebSocket.OPEN;
    }

    // ===========================================
    // Event Handlers
    // ===========================================

    /**
     * Handle successful connection
     */
    handleOpen() {
        console.log('✅ WebSocket connected');
        this.reconnectAttempts = 0;
        this.updateConnectionStatus('connected');
        this.emit('connected');
    }

    /**
     * Handle incoming messages
     */
    handleMessage(event) {
        try {
            const data = JSON.parse(event.data);
            console.log('📨 WebSocket message:', data);

            const { event_type, payload } = data;

            switch (event_type) {
                case 'task_created':
                    this.emit('task:created', payload);
                    break;
                case 'task_updated':
                    this.emit('task:updated', payload);
                    break;
                case 'task_deleted':
                    this.emit('task:deleted', payload);
                    break;
                case 'urgency_updated':
                    this.emit('urgency:updated', payload);
                    break;
                case 'notification':
                    this.emit('notification', payload);
                    break;
                default:
                    console.warn('Unknown WebSocket event:', event_type);
            }
        } catch (error) {
            console.error('Failed to parse WebSocket message:', error);
        }
    }

    /**
     * Handle connection close
     */
    handleClose(event) {
        console.log(`🔌 WebSocket closed: ${event.code} - ${event.reason}`);
        this.updateConnectionStatus('disconnected');
        this.emit('disconnected');

        // Attempt reconnection if not intentional close
        if (event.code !== 1000 && this.userId) {
            this.attemptReconnect();
        }
    }

    /**
     * Handle connection error
     */
    handleError(error) {
        console.error('❌ WebSocket error:', error);
        this.updateConnectionStatus('disconnected');
        this.emit('error', error);
    }

    /**
     * Attempt to reconnect
     */
    attemptReconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.error('Max reconnection attempts reached');
            this.emit('reconnect:failed');
            return;
        }

        this.reconnectAttempts++;
        const delay = this.reconnectDelay * this.reconnectAttempts;

        console.log(`🔄 Reconnecting in ${delay / 1000}s... (attempt ${this.reconnectAttempts})`);

        this.updateConnectionStatus('reconnecting');
        this.emit('reconnecting', { attempt: this.reconnectAttempts });

        setTimeout(() => {
            if (this.userId) {
                this.connect(this.userId);
            }
        }, delay);
    }

    // ===========================================
    // Event System
    // ===========================================

    /**
     * Subscribe to an event
     */
    on(event, callback) {
        if (!this.listeners.has(event)) {
            this.listeners.set(event, new Set());
        }
        this.listeners.get(event).add(callback);

        // Return unsubscribe function
        return () => this.off(event, callback);
    }

    /**
     * Unsubscribe from an event
     */
    off(event, callback) {
        if (this.listeners.has(event)) {
            this.listeners.get(event).delete(callback);
        }
    }

    /**
     * Emit an event to all listeners
     */
    emit(event, data = null) {
        if (this.listeners.has(event)) {
            this.listeners.get(event).forEach(callback => {
                try {
                    callback(data);
                } catch (error) {
                    console.error(`Error in WebSocket listener [${event}]:`, error);
                }
            });
        }
    }

    // ===========================================
    // UI Helpers
    // ===========================================

    /**
     * Update connection status in UI
     */
    updateConnectionStatus(status) {
        const statusElement = document.getElementById('connection-status');
        if (!statusElement) return;

        statusElement.className = `connection-status ${status}`;

        const textElement = statusElement.querySelector('.status-text');
        if (textElement) {
            switch (status) {
                case 'connected':
                    textElement.textContent = 'Connected';
                    break;
                case 'disconnected':
                    textElement.textContent = 'Disconnected';
                    break;
                case 'reconnecting':
                    textElement.textContent = 'Reconnecting...';
                    break;
                default:
                    textElement.textContent = 'Connecting...';
            }
        }
    }
}

// Create singleton instance
const wsManager = new WebSocketManager();

export { wsManager, WebSocketManager };
export default wsManager;
