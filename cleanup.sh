#!/bin/bash
# Cleanup script for GitSummarizer-RAG

echo -e "\033[0;36mCleaning up cached directories...\033[0m"

# Clean frontend caches
if [ -d "frontend/.next" ]; then
    echo -e "\033[0;33mRemoving frontend/.next directory...\033[0m"
    rm -rf frontend/.next
fi

# Clean backend caches
echo -e "\033[0;33mRemoving Python cache directories...\033[0m"
find backend -name "__pycache__" -type d -exec rm -rf {} +

# Clean root __pycache__ if it exists
if [ -d "__pycache__" ]; then
    echo -e "\033[0;33mRemoving root __pycache__ directory...\033[0m"
    rm -rf __pycache__
fi

# Clean temporary repo directory
if [ -d "temp_repos" ]; then
    echo -e "\033[0;33mRemoving temp_repos directory...\033[0m"
    rm -rf temp_repos
    # Recreate the directory
    mkdir -p temp_repos
fi

# Also create a temp_repos directory in the backend if it doesn't exist
if [ ! -d "backend/temp_repos" ]; then
    echo -e "\033[0;33mCreating backend/temp_repos directory...\033[0m"
    mkdir -p backend/temp_repos
fi

echo -e "\033[0;32mCleanup complete!\033[0m"
echo -e "\033[0;32mYou can now start the backend and frontend applications.\033[0m"
echo -e "\033[0m"
echo -e "\033[0;36mTo start the backend:\033[0m"
echo -e "  cd backend"
echo -e "  python api.py"
echo -e "\033[0m"
echo -e "\033[0;36mTo start the frontend:\033[0m"
echo -e "  cd frontend"
echo -e "  npm install"
echo -e "  npm run dev" 