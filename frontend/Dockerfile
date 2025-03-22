FROM node:18-alpine

WORKDIR /app

# Copy package.json and package-lock.json
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy the rest of the application
COPY . .

# Copy the .env.production to .env
RUN cp .env.production .env || echo "No production env file"

# Expose the port the app runs on
EXPOSE 3000

# Command to run the application
CMD ["npm", "start"] 