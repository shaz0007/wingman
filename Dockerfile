# Stage 1: Build static frontend assets
FROM node:22-alpine as builder

WORKDIR /app

# Copy dependency specifications
COPY package.json package-lock.json ./
RUN npm ci

# Copy source code and config
COPY tsconfig*.json vite.config.ts index.html ./
COPY public ./public
COPY src ./src

# Build production bundle
RUN npm run build

# Stage 2: Serve static bundle with high-performance Nginx
FROM nginx:alpine

# Remove default nginx configuration
RUN rm /etc/nginx/conf.d/default.conf

# Copy custom Nginx configuration with API proxy and security headers
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy compiled frontend assets from builder
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD wget --quiet --tries=1 --spider http://localhost/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
