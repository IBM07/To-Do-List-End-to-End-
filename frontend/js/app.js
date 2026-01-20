/**
 * ===========================================
 * AuraTask - Main Application Module
 * ===========================================
 * Handles app state, rendering, and user interactions
 */

import api from './api.js';
import wsManager from './websocket.js';

// ===========================================
// Application State
// ===========================================

const AppState = {
    user: null,
    tasks: [],
    isLoading: false,
    showCompleted: false,
};

// ===========================================
// DOM Elements Cache
// ===========================================

const DOM = {
    // Sections
    authSection: document.getElementById('auth-section'),
    dashboardSection: document.getElementById('dashboard-section'),

    // Auth Forms
    loginForm: document.getElementById('login-form'),
    registerForm: document.getElementById('register-form'),
    authTabs: document.querySelectorAll('.auth-tab'),
    authError: document.getElementById('auth-error'),

    // Dashboard
    userEmail: document.getElementById('user-email'),
    userTimezone: document.getElementById('user-timezone'),
    logoutBtn: document.getElementById('logout-btn'),
    smartInput: document.getElementById('smart-input'),
    addTaskBtn: document.getElementById('add-task-btn'),

    // Task Columns
    overdueTasksEl: document.getElementById('overdue-tasks'),
    dueSoonTasksEl: document.getElementById('due-soon-tasks'),
    upcomingTasksEl: document.getElementById('upcoming-tasks'),

    // Counts
    overdueCount: document.getElementById('overdue-count'),
    dueSoonCount: document.getElementById('due-soon-count'),
    upcomingCount: document.getElementById('upcoming-count'),
    completedCount: document.getElementById('completed-count'),

    // Completed Section
    toggleCompletedBtn: document.getElementById('toggle-completed'),
    completedTasksEl: document.getElementById('completed-tasks'),

    // Template
    taskCardTemplate: document.getElementById('task-card-template'),

    // Toast
    toastContainer: document.getElementById('toast-container'),
};

// ===========================================
// Initialization
// ===========================================

document.addEventListener('DOMContentLoaded', () => {
    setupEventListeners();
    checkAuthState();
});

async function checkAuthState() {
    if (api.isAuthenticated()) {
        try {
            AppState.user = await api.getMe();
            showDashboard();
            await loadTasks();
            connectWebSocket();
        } catch (error) {
            // Token expired or invalid
            api.clearToken();
            showAuth();
        }
    } else {
        showAuth();
    }
}

// ===========================================
// Event Listeners Setup
// ===========================================

function setupEventListeners() {
    // Auth tabs
    DOM.authTabs.forEach(tab => {
        tab.addEventListener('click', () => switchAuthTab(tab.dataset.tab));
    });

    // Auth forms
    DOM.loginForm.addEventListener('submit', handleLogin);
    DOM.registerForm.addEventListener('submit', handleRegister);

    // Logout
    DOM.logoutBtn.addEventListener('click', handleLogout);

    // Smart input
    DOM.smartInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') handleAddTask();
    });
    DOM.addTaskBtn.addEventListener('click', handleAddTask);

    // Completed toggle
    DOM.toggleCompletedBtn.addEventListener('click', toggleCompletedSection);

    // Listen for auth:logout event
    window.addEventListener('auth:logout', () => {
        wsManager.disconnect();
        showAuth();
    });

    // WebSocket events
    wsManager.on('task:created', (task) => {
        addTaskToState(task);
        renderTasks();
        showToast('Task created!', 'success');
    });

    wsManager.on('task:updated', (task) => {
        updateTaskInState(task);
        renderTasks();
    });

    wsManager.on('task:deleted', ({ task_id }) => {
        removeTaskFromState(task_id);
        renderTasks();
        showToast('Task deleted', 'info');
    });

    wsManager.on('urgency:updated', (updates) => {
        updates.forEach(update => {
            const task = AppState.tasks.find(t => t.id === update.task_id);
            if (task) {
                task.urgency_score = update.urgency_score;
            }
        });
        renderTasks();
    });
}

// ===========================================
// Authentication Handlers
// ===========================================

function switchAuthTab(tab) {
    DOM.authTabs.forEach(t => t.classList.toggle('active', t.dataset.tab === tab));
    DOM.loginForm.classList.toggle('hidden', tab !== 'login');
    DOM.registerForm.classList.toggle('hidden', tab !== 'register');
    hideAuthError();
}

async function handleLogin(e) {
    e.preventDefault();

    const email = document.getElementById('login-email').value;
    const password = document.getElementById('login-password').value;

    setButtonLoading(e.target.querySelector('button'), true);
    hideAuthError();

    try {
        await api.login(email, password);
        AppState.user = await api.getMe();
        showDashboard();
        await loadTasks();
        connectWebSocket();
    } catch (error) {
        showAuthError(error.message);
    } finally {
        setButtonLoading(e.target.querySelector('button'), false);
    }
}

async function handleRegister(e) {
    e.preventDefault();

    const email = document.getElementById('register-email').value;
    const password = document.getElementById('register-password').value;
    const timezone = document.getElementById('register-timezone').value;

    setButtonLoading(e.target.querySelector('button'), true);
    hideAuthError();

    try {
        await api.register(email, password, timezone);
        // Auto-login after registration
        await api.login(email, password);
        AppState.user = await api.getMe();
        showDashboard();
        await loadTasks();
        connectWebSocket();
    } catch (error) {
        showAuthError(error.message);
    } finally {
        setButtonLoading(e.target.querySelector('button'), false);
    }
}

function handleLogout() {
    api.logout();
    wsManager.disconnect();
    AppState.user = null;
    AppState.tasks = [];
    showAuth();
}

function showAuthError(message) {
    DOM.authError.textContent = message;
    DOM.authError.classList.remove('hidden');
}

function hideAuthError() {
    DOM.authError.classList.add('hidden');
}

// ===========================================
// View Switching
// ===========================================

function showAuth() {
    DOM.authSection.classList.remove('hidden');
    DOM.dashboardSection.classList.add('hidden');
    DOM.loginForm.reset();
    DOM.registerForm.reset();
    switchAuthTab('login');
}

function showDashboard() {
    DOM.authSection.classList.add('hidden');
    DOM.dashboardSection.classList.remove('hidden');

    if (AppState.user) {
        DOM.userEmail.textContent = AppState.user.email;
        DOM.userTimezone.textContent = AppState.user.timezone;
    }
}

// ===========================================
// Task Management
// ===========================================

async function loadTasks() {
    try {
        AppState.isLoading = true;
        const response = await api.getTasks({ include_completed: true, per_page: 100 });
        AppState.tasks = response.tasks || [];
        renderTasks();
    } catch (error) {
        showToast('Failed to load tasks', 'error');
        console.error('Failed to load tasks:', error);
    } finally {
        AppState.isLoading = false;
    }
}

async function handleAddTask() {
    const input = DOM.smartInput.value.trim();
    if (!input) return;

    setButtonLoading(DOM.addTaskBtn, true);

    try {
        const task = await api.createTask({ nlp_input: input });
        addTaskToState(task);
        renderTasks();
        DOM.smartInput.value = '';
        showToast('Task created!', 'success');
    } catch (error) {
        showToast(error.message || 'Failed to create task', 'error');
    } finally {
        setButtonLoading(DOM.addTaskBtn, false);
    }
}

async function handleCompleteTask(taskId) {
    try {
        await api.completeTask(taskId);
        const task = AppState.tasks.find(t => t.id === taskId);
        if (task) {
            task.status = 'COMPLETED';
        }
        renderTasks();
        showToast('Task completed! 🎉', 'success');
    } catch (error) {
        showToast('Failed to complete task', 'error');
    }
}

async function handleSnoozeTask(taskId) {
    try {
        await api.snoozeTask(taskId, 60);
        showToast('Snoozed for 1 hour 💤', 'info');
    } catch (error) {
        showToast('Failed to snooze task', 'error');
    }
}

async function handleDeleteTask(taskId) {
    if (!confirm('Delete this task?')) return;

    try {
        await api.deleteTask(taskId);
        removeTaskFromState(taskId);
        renderTasks();
        showToast('Task deleted', 'info');
    } catch (error) {
        showToast('Failed to delete task', 'error');
    }
}

// ===========================================
// State Management
// ===========================================

function addTaskToState(task) {
    const existingIndex = AppState.tasks.findIndex(t => t.id === task.id);
    if (existingIndex >= 0) {
        AppState.tasks[existingIndex] = task;
    } else {
        AppState.tasks.push(task);
    }
}

function updateTaskInState(task) {
    const index = AppState.tasks.findIndex(t => t.id === task.id);
    if (index >= 0) {
        AppState.tasks[index] = task;
    }
}

function removeTaskFromState(taskId) {
    AppState.tasks = AppState.tasks.filter(t => t.id !== taskId);
}

// ===========================================
// Rendering
// ===========================================

function renderTasks() {
    const now = new Date();
    const in24Hours = new Date(now.getTime() + 24 * 60 * 60 * 1000);

    // Categorize tasks
    const overdueTasks = [];
    const dueSoonTasks = [];
    const upcomingTasks = [];
    const completedTasks = [];

    AppState.tasks.forEach(task => {
        if (task.status === 'COMPLETED') {
            completedTasks.push(task);
            return;
        }

        const dueDate = new Date(task.due_date);

        if (dueDate < now) {
            overdueTasks.push(task);
        } else if (dueDate <= in24Hours) {
            dueSoonTasks.push(task);
        } else {
            upcomingTasks.push(task);
        }
    });

    // Sort by urgency score (descending)
    const sortByUrgency = (a, b) => (b.urgency_score || 0) - (a.urgency_score || 0);
    overdueTasks.sort(sortByUrgency);
    dueSoonTasks.sort(sortByUrgency);
    upcomingTasks.sort(sortByUrgency);

    // Render each column
    renderTaskList(DOM.overdueTasksEl, overdueTasks, true);
    renderTaskList(DOM.dueSoonTasksEl, dueSoonTasks, false);
    renderTaskList(DOM.upcomingTasksEl, upcomingTasks, false);
    renderTaskList(DOM.completedTasksEl, completedTasks, false);

    // Update counts
    DOM.overdueCount.textContent = overdueTasks.length;
    DOM.dueSoonCount.textContent = dueSoonTasks.length;
    DOM.upcomingCount.textContent = upcomingTasks.length;
    DOM.completedCount.textContent = completedTasks.length;
}

function renderTaskList(container, tasks, isOverdue) {
    container.innerHTML = '';

    if (tasks.length === 0) {
        container.innerHTML = '<p class="empty-message" style="color: var(--color-text-muted); text-align: center; padding: 2rem;">No tasks</p>';
        return;
    }

    tasks.forEach(task => {
        const card = createTaskCard(task, isOverdue);
        container.appendChild(card);
    });
}

function createTaskCard(task, isOverdue = false) {
    const template = DOM.taskCardTemplate.content.cloneNode(true);
    const card = template.querySelector('.task-card');

    card.dataset.taskId = task.id;
    if (isOverdue) card.classList.add('overdue');

    // Priority badge
    const priorityBadge = card.querySelector('.priority-badge');
    priorityBadge.textContent = task.priority;
    priorityBadge.classList.add(`priority-${task.priority}`);

    // Urgency score
    const urgencyScore = card.querySelector('.urgency-score');
    urgencyScore.textContent = `Score: ${(task.urgency_score || 0).toFixed(1)}`;

    // Title and description
    card.querySelector('.task-title').textContent = task.title;
    card.querySelector('.task-description').textContent = task.description || '';

    // Due date
    card.querySelector('.due-date').textContent = `📅 ${task.due_date_human || formatDate(task.due_date)}`;

    // Action buttons
    card.querySelector('.btn-complete').addEventListener('click', (e) => {
        e.stopPropagation();
        handleCompleteTask(task.id);
    });

    card.querySelector('.btn-snooze').addEventListener('click', (e) => {
        e.stopPropagation();
        handleSnoozeTask(task.id);
    });

    card.querySelector('.btn-delete').addEventListener('click', (e) => {
        e.stopPropagation();
        handleDeleteTask(task.id);
    });

    return card;
}

function toggleCompletedSection() {
    AppState.showCompleted = !AppState.showCompleted;
    DOM.completedTasksEl.classList.toggle('hidden', !AppState.showCompleted);
    DOM.toggleCompletedBtn.querySelector('span').textContent =
        AppState.showCompleted ? 'Hide Completed' : 'Show Completed';
}

// ===========================================
// WebSocket Connection
// ===========================================

function connectWebSocket() {
    if (AppState.user) {
        wsManager.connect(AppState.user.id);
    }
}

// ===========================================
// Utility Functions
// ===========================================

function formatDate(dateStr) {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    return date.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
        hour12: true,
    });
}

function setButtonLoading(button, isLoading) {
    if (!button) return;

    const textSpan = button.querySelector('span:not(.btn-loader)');
    const loaderSpan = button.querySelector('.btn-loader');

    button.disabled = isLoading;

    if (textSpan) textSpan.classList.toggle('hidden', isLoading);
    if (loaderSpan) loaderSpan.classList.toggle('hidden', !isLoading);
}

function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;

    DOM.toastContainer.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100%)';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// Export for debugging
window.AppState = AppState;
window.api = api;
