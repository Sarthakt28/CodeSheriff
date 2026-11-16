# ── Stage 1: Build ─────────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files first (better Docker layer caching)
# If only source code changes, npm install won't re-run
COPY package.json package-lock.json* ./
RUN npm install --frozen-lockfile

# Copy source and build
COPY . .
RUN npm run build
# Output: /app/dist — optimized React bundle


# ── Stage 2: Serve ─────────────────────────────────────────────────
FROM nginx:1.27-alpine

# Remove default nginx config
RUN rm /etc/nginx/conf.d/default.conf

# Copy our custom nginx config (handles SPA routing + API proxy)
COPY nginx.conf /etc/nginx/conf.d/codesheriff.conf

# Copy the built React app from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
