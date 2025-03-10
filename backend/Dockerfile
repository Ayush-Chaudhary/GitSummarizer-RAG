FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create temp_repos directory
RUN mkdir -p temp_repos

# Expose port
EXPOSE 8000

# Run the API server
CMD ["python", "api.py"] 