FROM node:18-alpine

WORKDIR /app

# This is a placeholder Dockerfile for the frontend
# It will be updated once the frontend implementation is ready

# For now, just create a simple HTTP server to serve a placeholder page
RUN npm install -g http-server
COPY . /app

# Create a simple placeholder HTML page
RUN echo '<html><body><h1>JEAN Frontend</h1><p>This is a placeholder. Frontend implementation coming soon.</p></body></html>' > index.html

EXPOSE 3000

CMD ["http-server", "-p", "3000"] 