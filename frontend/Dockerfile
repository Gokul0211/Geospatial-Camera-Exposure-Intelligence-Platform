# ── Stage 1: Build ────────────────────────────────────────────────────────────
FROM node:20-alpine AS build

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .
RUN npm run build


# ── Stage 2: Serve with nginx ──────────────────────────────────────────────────
FROM nginx:alpine

# Copy the built React app
COPY --from=build /app/dist /usr/share/nginx/html

# Custom nginx config that proxies /api → backend service.
# This is the fix for: "Vite's dev proxy doesn't run in the production nginx container."
# Inside Docker Compose, backend is reachable at http://backend:8000.
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
