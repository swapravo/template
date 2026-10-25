# syntax=docker/dockerfile:1

# Stage 1: Build the static Astro site
FROM node:22-alpine AS builder
WORKDIR /app

# Disable Astro telemetry during build
ENV ASTRO_TELEMETRY_DISABLED=1

COPY package.json package-lock.json* ./
RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi

COPY . .

# PUBLIC_* vars are inlined into the static output at build time
ARG PUBLIC_API_URL
ENV PUBLIC_API_URL=${PUBLIC_API_URL}

RUN npm run build

# Stage 2: Serve the static output
FROM nginx:alpine AS runner
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80
