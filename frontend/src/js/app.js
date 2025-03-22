/**
 * Main application script for GitSummarizer frontend
 */
document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const repoUrlInput = document.getElementById('repo-url');
    const loadRepoBtn = document.getElementById('load-repo-btn');
    const statusContainer = document.getElementById('status-container');
    const statusMessage = document.getElementById('status-message');
    const progressIndicator = document.getElementById('progress-indicator');
    const resultSection = document.getElementById('result-section');
    const repoInputSection = document.getElementById('repo-input-section');
    const chatMessages = document.getElementById('chat-messages');
    const queryInput = document.getElementById('query-input');
    const sendQueryBtn = document.getElementById('send-query-btn');
    const repoSummary = document.getElementById('repo-summary');
    const resetBtn = document.getElementById('reset-btn');
    const tabButtons = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');
    
    // Current repository URL
    let currentRepoUrl = '';
    // Status check interval
    let statusInterval = null;
    // Flag to track if we're currently processing
    let isProcessing = false;
    
    // Initialize the application
    function init() {
        bindEventListeners();
        setupNavigationProtection();
    }
    
    // Set up navigation protection to prevent leaving during processing
    function setupNavigationProtection() {
        // Check if we should prevent navigation
        async function shouldPreventNavigation() {
            if (!isProcessing) return false;
            
            try {
                // Double-check with the server if it's safe to restart
                const canRestart = await API.canRestart();
                return !canRestart;
            } catch (error) {
                console.error('Error checking if navigation is safe:', error);
                return isProcessing; // Fall back to local state
            }
        }
        
        // Handle beforeunload event
        window.addEventListener('beforeunload', async (e) => {
            if (await shouldPreventNavigation()) {
                // Display confirmation dialog
                e.preventDefault();
                e.returnValue = 'Changes you made may not be saved. Are you sure you want to leave?';
                return e.returnValue;
            }
        });
    }
    
    // Bind event listeners to DOM elements
    function bindEventListeners() {
        // Load repository button
        loadRepoBtn.addEventListener('click', handleLoadRepository);
        
        // Enter key for repository URL input
        repoUrlInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                handleLoadRepository();
            }
        });
        
        // Send query button
        sendQueryBtn.addEventListener('click', handleSendQuery);
        
        // Enter key for query input
        queryInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                handleSendQuery();
            }
        });
        
        // Reset button
        resetBtn.addEventListener('click', handleReset);
        
        // Tab switching
        tabButtons.forEach(button => {
            button.addEventListener('click', () => {
                const tabName = button.getAttribute('data-tab');
                switchTab(tabName);
            });
        });
    }
    
    // Handle repository loading
    async function handleLoadRepository() {
        const repoUrl = repoUrlInput.value.trim();
        
        if (!repoUrl) {
            alert('Please enter a GitHub repository URL');
            return;
        }
        
        // Show loading status
        loadRepoBtn.disabled = true;
        statusContainer.classList.remove('hidden');
        statusMessage.textContent = 'Initiating repository analysis...';
        progressIndicator.style.width = '10%';
        
        try {
            // Request repository loading
            const response = await API.loadRepository(repoUrl);
            
            if (response.success) {
                currentRepoUrl = repoUrl;
                isProcessing = true;
                startStatusChecking();
            } else {
                showError('Failed to start processing repository: ' + response.message);
                isProcessing = false;
            }
        } catch (error) {
            showError('Error connecting to server');
            console.error(error);
            isProcessing = false;
        }
    }
    
    // Start checking repository status periodically
    function startStatusChecking() {
        // Clear any existing interval
        if (statusInterval) {
            clearInterval(statusInterval);
        }
        
        // Check status immediately
        checkRepositoryStatus();
        
        // Then check every 2 seconds
        statusInterval = setInterval(checkRepositoryStatus, 2000);
    }
    
    // Check repository status
    async function checkRepositoryStatus() {
        try {
            const status = await API.getRepositoryStatus(currentRepoUrl);
            
            // Update status message
            statusMessage.textContent = status.details.message || 'Processing repository...';
            
            // Update progress based on stage
            switch (status.status) {
                case 'initializing':
                    progressIndicator.style.width = '20%';
                    isProcessing = true;
                    break;
                case 'queued':
                    progressIndicator.style.width = '10%';
                    isProcessing = true;
                    break;
                case 'ready':
                    progressIndicator.style.width = '100%';
                    clearInterval(statusInterval);
                    isProcessing = false;
                    showResultsSection();
                    loadRepositorySummary();
                    break;
                case 'error':
                    progressIndicator.style.width = '100%';
                    showError(status.details.message || 'Error processing repository');
                    clearInterval(statusInterval);
                    isProcessing = false;
                    break;
                default:
                    // For other stages, show incremental progress
                    progressIndicator.style.width = '50%';
                    isProcessing = true;
            }
            
        } catch (error) {
            showError('Error checking repository status');
            clearInterval(statusInterval);
            isProcessing = false;
            console.error(error);
        }
    }
    
    // Handle sending a query
    async function handleSendQuery() {
        const query = queryInput.value.trim();
        
        if (!query) {
            alert('Please enter a query');
            return;
        }
        
        // Add user message to chat
        addChatMessage(query, 'user');
        
        // Clear input
        queryInput.value = '';
        
        try {
            // Show loading message
            addChatMessage('Thinking...', 'system loading');
            
            // Send query to API
            const response = await API.queryRepository(currentRepoUrl, query);
            
            // Remove loading message
            const loadingMessage = chatMessages.querySelector('.loading');
            if (loadingMessage) {
                chatMessages.removeChild(loadingMessage);
            }
            
            // Display response
            addChatMessage(response.answer, 'system');
            
        } catch (error) {
            addChatMessage('Error: Failed to get a response', 'system error');
            console.error(error);
        }
    }
    
    // Add a message to the chat
    function addChatMessage(message, type) {
        const messageEl = document.createElement('div');
        messageEl.classList.add('chat-message');
        messageEl.classList.add(type === 'user' ? 'user-message' : 'system-message');
        
        if (type === 'system loading') {
            messageEl.classList.add('loading');
        }
        
        messageEl.textContent = message;
        chatMessages.appendChild(messageEl);
        
        // Scroll to bottom
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    
    // Load repository summary
    async function loadRepositorySummary() {
        try {
            repoSummary.textContent = 'Loading summary...';
            
            const response = await API.getRepositorySummary(currentRepoUrl);
            
            if (response.summary) {
                repoSummary.textContent = response.summary;
            } else {
                repoSummary.textContent = 'No summary available';
            }
            
        } catch (error) {
            repoSummary.textContent = 'Error loading summary';
            console.error(error);
        }
    }
    
    // Switch between tabs
    function switchTab(tabName) {
        // Update button active state
        tabButtons.forEach(btn => {
            if (btn.getAttribute('data-tab') === tabName) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        });
        
        // Update content visibility
        tabContents.forEach(content => {
            if (content.id === `${tabName}-tab`) {
                content.classList.add('active');
            } else {
                content.classList.remove('active');
            }
        });
    }
    
    // Show the results section
    function showResultsSection() {
        repoInputSection.classList.add('hidden');
        resultSection.classList.remove('hidden');
        resetBtn.classList.remove('hidden');
    }
    
    // Show the input section
    function showInputSection() {
        resultSection.classList.add('hidden');
        repoInputSection.classList.remove('hidden');
        resetBtn.classList.add('hidden');
        statusContainer.classList.add('hidden');
        loadRepoBtn.disabled = false;
    }
    
    // Handle reset button
    async function handleReset() {
        // Check if it's safe to reset
        if (isProcessing) {
            const canRestart = await API.canRestart();
            if (!canRestart) {
                alert('Processing is in progress. Please wait until it completes.');
                return;
            }
        }
        
        // Clear chat messages
        chatMessages.innerHTML = '';
        
        // Clear repository summary
        repoSummary.textContent = '';
        
        // Reset repository URL input
        repoUrlInput.value = '';
        
        // Stop status checking
        if (statusInterval) {
            clearInterval(statusInterval);
            statusInterval = null;
        }
        
        // Unload repository in the background
        if (currentRepoUrl) {
            API.unloadRepository(currentRepoUrl)
                .catch(error => console.error('Error unloading repository:', error));
            currentRepoUrl = '';
        }
        
        // Show input section
        showInputSection();
        isProcessing = false;
    }
    
    // Show error message
    function showError(message) {
        statusMessage.textContent = message;
        statusMessage.style.color = 'var(--error-color)';
        loadRepoBtn.disabled = false;
    }
    
    // Initialize the application
    init();
}); 