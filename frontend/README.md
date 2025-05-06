# JEAN Frontend

This directory contains the frontend application for JEAN.

## Overview

The frontend serves a simple purpose - to authenticate users with Google and provide them with their MCP configuration URL for use with Claude Desktop, Cursor, or other MCP-compatible clients.

## Components

### Server

- `server.js` - Express server that serves static files and handles Google OAuth callback
- `package.json` - Node.js package configuration

### User Interface

- `/public/index.html` - Landing page with Google Sign-In
- `/public/profile.html` - Profile page showing the MCP configuration
- `/public/css/styles.css` - Styling for all pages

## Flow

1. User visits the site and clicks "Sign in with Google"
2. After authentication, they are redirected to the profile page
3. The profile page displays their unique MCP configuration
4. User copies this configuration to their Claude Desktop or Cursor settings

## Development

To run the frontend locally:

```bash
# Install dependencies
npm install

# Start the development server
npm run dev
```

## Docker Deployment

The frontend is containerized and can be run with Docker:

```bash
# Build the image
docker build -t jean-frontend .

# Run the container
docker run -p 3000:3000 -e BACKEND_URL=http://localhost:8000 jean-frontend
```

## Configuration

The frontend is configured via environment variables:

- `PORT` - Port to run the server on (default: 3000)
- `BACKEND_URL` - URL of the JEAN backend (default: http://localhost:8000)

Google OAuth requires configuring the OAuth client ID in `public/index.html`.

## Next Steps

1. Complete the Google OAuth integration by filling in the client ID
2. Add user profile management functionality if needed
3. Enhance the UI with additional styling and features
4. Add support for MCP configuration testing 