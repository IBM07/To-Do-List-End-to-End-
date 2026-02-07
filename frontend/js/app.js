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

    // Edit Modal
    editModal: document.getElementById('edit-modal'),
    editTaskForm: document.getElementById('edit-task-form'),
    editTaskId: document.getElementById('edit-task-id'),
    editTitle: document.getElementById('edit-title'),
    editDescription: document.getElementById('edit-description'),
    editPriority: document.getElementById('edit-priority'),
    editDueDate: document.getElementById('edit-due-date'),
    cancelEditBtn: document.getElementById('cancel-edit'),

    // Settings Modal
    settingsBtn: document.getElementById('settings-btn'),
    settingsModal: document.getElementById('settings-modal'),
    settingsForm: document.getElementById('settings-form'),
    telegramChatId: document.getElementById('telegram-chat-id'),
    discordWebhook: document.getElementById('discord-webhook'),
    closeSettingsBtn: document.getElementById('close-settings'),
    cancelSettingsBtn: document.getElementById('cancel-settings'),
};

// ===========================================
// Initialization
// ===========================================

document.addEventListener('DOMContentLoaded', () => {
    detectAndSetTimezone();
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

/**
 * Detect browser timezone and set it in the registration form.
 */
function detectAndSetTimezone() {
    try {
        // Get browser's timezone using Intl API
        const detectedTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
        console.log('[Timezone] Detected:', detectedTimezone);

        // Store in AppState for use during registration
        AppState.detectedTimezone = detectedTimezone;

        // Try to set the dropdown value
        const timezoneSelect = document.getElementById('register-timezone');
        if (timezoneSelect) {
            // Check if detected timezone is in the dropdown options
            const optionExists = Array.from(timezoneSelect.options).some(
                opt => opt.value === detectedTimezone
            );

            if (optionExists) {
                timezoneSelect.value = detectedTimezone;
            } else {
                // Add the detected timezone as a new option and select it
                const newOption = document.createElement('option');
                newOption.value = detectedTimezone;
                newOption.textContent = detectedTimezone;
                newOption.selected = true;
                timezoneSelect.insertBefore(newOption, timezoneSelect.firstChild);
            }
        }
    } catch (error) {
        console.warn('[Timezone] Detection failed:', error);
        AppState.detectedTimezone = 'UTC';
    }
}

/**
 * Get the current timezone (detected or selected).
 */
function getCurrentTimezone() {
    const timezoneSelect = document.getElementById('register-timezone');
    return timezoneSelect?.value || AppState.detectedTimezone || 'UTC';
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

    // Edit modal
    DOM.editTaskForm.addEventListener('submit', handleSaveEdit);
    DOM.cancelEditBtn.addEventListener('click', closeEditModal);
    DOM.editModal.querySelector('.modal-close').addEventListener('click', closeEditModal);
    DOM.editModal.addEventListener('click', (e) => {
        if (e.target === DOM.editModal) closeEditModal();
    });

    // Settings modal
    DOM.settingsBtn.addEventListener('click', openSettingsModal);
    DOM.settingsForm.addEventListener('submit', handleSaveSettings);
    DOM.closeSettingsBtn.addEventListener('click', closeSettingsModal);
    DOM.cancelSettingsBtn.addEventListener('click', closeSettingsModal);
    DOM.settingsModal.addEventListener('click', (e) => {
        if (e.target === DOM.settingsModal) closeSettingsModal();
    });

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
    // Use auto-detected timezone or dropdown selection
    const timezone = getCurrentTimezone();
    console.log('[Register] Using timezone:', timezone);

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

        // Use due_date_local if available (user's timezone), fallback to due_date
        const dueDateStr = task.due_date_local || task.due_date;
        const dueDate = new Date(dueDateStr);

        // Compare using timestamps for accuracy
        if (dueDate.getTime() < now.getTime()) {
            overdueTasks.push(task);
        } else if (dueDate.getTime() <= in24Hours.getTime()) {
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

    card.querySelector('.btn-edit').addEventListener('click', (e) => {
        e.stopPropagation();
        openEditModal(task);
    });

    // Render Subtasks
    renderSubtasksForCard(card, task);

    return card;
}

function toggleCompletedSection() {
    AppState.showCompleted = !AppState.showCompleted;
    DOM.completedTasksEl.classList.toggle('hidden', !AppState.showCompleted);
    DOM.toggleCompletedBtn.querySelector('span').textContent =
        AppState.showCompleted ? 'Hide Completed' : 'Show Completed';
}

// ===========================================
// Edit Modal Functions
// ===========================================

function openEditModal(task) {
    // Populate form with task data
    DOM.editTaskId.value = task.id;
    DOM.editTitle.value = task.title;
    DOM.editDescription.value = task.description || '';
    DOM.editPriority.value = task.priority;

    // Format due date for datetime-local input
    const dueDate = new Date(task.due_date);
    const localDateTime = new Date(dueDate.getTime() - dueDate.getTimezoneOffset() * 60000)
        .toISOString()
        .slice(0, 16);
    DOM.editDueDate.value = localDateTime;

    // Show modal
    DOM.editModal.classList.remove('hidden');
    DOM.editTitle.focus();
}

function closeEditModal() {
    DOM.editModal.classList.add('hidden');
    DOM.editTaskForm.reset();
}

async function handleSaveEdit(e) {
    e.preventDefault();

    const taskId = parseInt(DOM.editTaskId.value);
    const updates = {
        title: DOM.editTitle.value.trim(),
        description: DOM.editDescription.value.trim() || null,
        priority: DOM.editPriority.value,
        due_date: new Date(DOM.editDueDate.value).toISOString(),
    };

    try {
        const updatedTask = await api.updateTask(taskId, updates);
        updateTaskInState(updatedTask);
        renderTasks();
        closeEditModal();
        showToast('Task updated!', 'success');
    } catch (error) {
        showToast(error.message || 'Failed to update task', 'error');
    }
}

// ===========================================
// Settings Modal Functions
// ===========================================

async function openSettingsModal() {
    try {
        // Load current settings from API
        const settings = await api.getNotificationSettings();

        // Populate form
        DOM.telegramChatId.value = settings.telegram_chat_id || '';
        DOM.discordWebhook.value = settings.discord_webhook_url || '';

        // Show modal
        DOM.settingsModal.classList.remove('hidden');
    } catch (error) {
        showToast('Failed to load settings', 'error');
    }
}

function closeSettingsModal() {
    DOM.settingsModal.classList.add('hidden');
    DOM.settingsForm.reset();
}

async function handleSaveSettings(e) {
    e.preventDefault();

    // Always enable all notification channels
    const settings = {
        email_enabled: true,
        telegram_enabled: true,
        discord_enabled: true,
        telegram_chat_id: DOM.telegramChatId.value.trim() || null,
        discord_webhook_url: DOM.discordWebhook.value.trim() || null,
        notify_1hr_before: true,
        notify_24hr_before: true,
    };

    try {
        await api.updateNotificationSettings(settings);
        closeSettingsModal();
        showToast('Settings saved! 🎉', 'success');
    } catch (error) {
        showToast(error.message || 'Failed to save settings', 'error');
    }
}

// ===========================================
// Subtask Functions
// ===========================================

function renderSubtasksForCard(card, task) {
    const container = card.querySelector('.subtask-container');
    const list = card.querySelector('.subtask-list');
    const input = card.querySelector('.add-subtask-input');
    const addBtn = card.querySelector('.btn-add-subtask');

    // Show container if we have subtasks or to allow adding
    container.classList.remove('hidden');

    // Clear list
    list.innerHTML = '';

    // Render each subtask
    if (task.subtasks) {
        // Sort: completed at bottom, then by order
        // Note: Backend might already sort by order
        const sortedSubtasks = [...task.subtasks].sort((a, b) => {
            if (a.is_completed === b.is_completed) return a.order - b.order;
            return a.is_completed ? 1 : -1;
        });

        sortedSubtasks.forEach(subtask => {
            const item = document.createElement('div');
            item.className = 'subtask-item';

            // Checkbox
            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.className = 'subtask-checkbox';
            checkbox.checked = subtask.is_completed;
            checkbox.addEventListener('change', () => handleToggleSubtask(subtask.id));

            // Text
            const text = document.createElement('span');
            text.className = 'subtask-text';
            text.textContent = subtask.title;

            // Delete button
            const deleteBtn = document.createElement('button');
            deleteBtn.className = 'subtask-delete';
            deleteBtn.innerHTML = '&times;';
            deleteBtn.title = 'Delete subtask';
            deleteBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                handleDeleteSubtask(subtask.id);
            });

            item.appendChild(checkbox);
            item.appendChild(text);
            item.appendChild(deleteBtn);
            list.appendChild(item);
        });
    }

    // Event Listeners for Adding
    // Remove old listeners to prevent duplicates? 
    // Easier to clone the node and replace or use clean event handling.
    // Since we re-render the whole card, we don't need to worry about duplicates on the same element.

    // BUT 'card' is created fresh in createTaskCard!
    // So we can just add listener.

    const handleAdd = () => {
        const title = input.value.trim();
        if (title) {
            handleAddSubtask(task.id, title, input);
        }
    };

    addBtn.onclick = handleAdd;
    input.onkeypress = (e) => {
        if (e.key === 'Enter') handleAdd();
    };
}

async function handleAddSubtask(taskId, title, inputElement) {
    try {
        await api.createSubtask(taskId, title);
        inputElement.value = '';
        // UI update will happen via WebSocket broadcast 'task:updated'
    } catch (error) {
        showToast('Failed to add subtask', 'error');
    }
}

async function handleToggleSubtask(subtaskId) {
    try {
        await api.toggleSubtask(subtaskId);
        // UI update via WebSocket
    } catch (error) {
        showToast('Failed to toggle subtask', 'error');
    }
}

async function handleDeleteSubtask(subtaskId) {
    try {
        await api.deleteSubtask(subtaskId);
        // UI update via WebSocket
    } catch (error) {
        showToast('Failed to delete subtask', 'error');
    }
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
