# ==============================================================================
# CreatorIQ Frontend - Multi-Stage Production Container
# ==============================================================================

# ------------------------------------------------------------------------------
# Stage 1: Build Frontend Assets
# ------------------------------------------------------------------------------
FROM node:20-alpine AS builder

WORKDIR /app

# Copy dependency definitions
COPY package.json package-lock.json* ./

# Install project dependencies
RUN npm ci || npm install

# Copy application source
COPY . ./

# Build production bundle with Vite
RUN npm run build

# ------------------------------------------------------------------------------
# Stage 2: Serve via Production Nginx Server
# ------------------------------------------------------------------------------
FROM nginx:alpine

# Remove default nginx HTML assets
RUN rm -rf /usr/share/nginx/html/*

# Copy compiled assets from build stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy custom reverse proxy & SPA nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose HTTP port 80
EXPOSE 80

# Health check
HEALTHCHECK --interval=20s --timeout=5s --start-period=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://127.0.0.1:80/ || exit 1

# Start Nginx in foreground
CMD ["nginx", "-g", "daemon off;"]
