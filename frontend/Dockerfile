FROM node:18-alpine

WORKDIR /app

# Copy package.json and install dependencies
COPY package.json ./
RUN npm install

# Copy the rest of the application
COPY . .

# Create a .env file with default settings (will be overridden by environment variables)
RUN echo "PORT=3000\nBACKEND_URL=http://backend:8000" > .env

# Expose the port the app runs on
EXPOSE 3000

# Command to run the application
CMD ["node", "server.js"] 