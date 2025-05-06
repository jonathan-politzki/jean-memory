# Use an official Node.js runtime as a parent image
FROM node:18-alpine

# Set the working directory in the container
WORKDIR /usr/src/app

# Copy package.json and package-lock.json (if available)
# Ensure package-lock.json is committed to your repo if you have one
COPY package*.json ./

# Install application dependencies
RUN npm install

# Bundle app source
COPY . .

# Make port 3005 available to the world outside this container
EXPOSE 3005

# Define environment variables (can be overridden)
ENV PORT=3005
# The BACKEND_URL will be injected by docker-compose
# ENV BACKEND_URL=http://backend:8080 

# Run server.js when the container launches
CMD ["node", "server.js"] 