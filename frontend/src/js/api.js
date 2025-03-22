/**
 * API Service for communicating with the backend
 */
const API = {
    // Backend API base URL
    baseUrl: 'http://localhost:8000/api',
    
    /**
     * Load a GitHub repository for analysis
     * @param {string} repoUrl - The GitHub repository URL
     * @param {boolean} forceReload - Whether to force reload if already loaded
     * @returns {Promise<object>} Response from the API
     */
    loadRepository: async (repoUrl, forceReload = false) => {
        try {
            const response = await fetch(`${API.baseUrl}/repository`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    repo_url: repoUrl,
                    force_reload: forceReload
                })
            });
            
            return await response.json();
        } catch (error) {
            console.error('Error loading repository:', error);
            throw error;
        }
    },
    
    /**
     * Check the status of a repository being processed
     * @param {string} repoUrl - The GitHub repository URL
     * @returns {Promise<object>} Status information
     */
    getRepositoryStatus: async (repoUrl) => {
        try {
            const response = await fetch(`${API.baseUrl}/repository/status?repo_url=${encodeURIComponent(repoUrl)}`);
            return await response.json();
        } catch (error) {
            console.error('Error checking repository status:', error);
            throw error;
        }
    },
    
    /**
     * Query a loaded repository with a natural language question
     * @param {string} repoUrl - The GitHub repository URL
     * @param {string} query - The natural language query
     * @returns {Promise<object>} The answer from the API
     */
    queryRepository: async (repoUrl, query) => {
        try {
            const response = await fetch(`${API.baseUrl}/query`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    repo_url: repoUrl,
                    query: query
                })
            });
            
            return await response.json();
        } catch (error) {
            console.error('Error querying repository:', error);
            throw error;
        }
    },
    
    /**
     * Get a summary of a loaded repository
     * @param {string} repoUrl - The GitHub repository URL
     * @returns {Promise<object>} The repository summary
     */
    getRepositorySummary: async (repoUrl) => {
        try {
            const response = await fetch(`${API.baseUrl}/repository/summary?repo_url=${encodeURIComponent(repoUrl)}`);
            return await response.json();
        } catch (error) {
            console.error('Error getting repository summary:', error);
            throw error;
        }
    },
    
    /**
     * Unload a repository to free up resources
     * @param {string} repoUrl - The GitHub repository URL
     * @returns {Promise<object>} Response from the API
     */
    unloadRepository: async (repoUrl) => {
        try {
            const encodedUrl = encodeURIComponent(repoUrl);
            const response = await fetch(`${API.baseUrl}/repository/${encodedUrl}`, {
                method: 'DELETE'
            });
            
            return await response.json();
        } catch (error) {
            console.error('Error unloading repository:', error);
            throw error;
        }
    },
    
    /**
     * Check if it's safe to restart the server
     * @returns {Promise<boolean>} Whether it's safe to restart
     */
    canRestart: async () => {
        try {
            const response = await fetch(`${API.baseUrl}/can_restart`);
            const data = await response.json();
            return data.can_restart;
        } catch (error) {
            console.error('Error checking restart capability:', error);
            return true; // Default to true if we can't check
        }
    },
    
    /**
     * Check if the API is healthy
     * @returns {Promise<object>} Health status
     */
    healthCheck: async () => {
        try {
            const response = await fetch(`${API.baseUrl.replace('/api', '')}/health`);
            return await response.json();
        } catch (error) {
            console.error('Error checking API health:', error);
            throw error;
        }
    }
}; 