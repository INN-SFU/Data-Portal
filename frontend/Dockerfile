# ---- Stage 1: build React app ----
FROM node:20-alpine AS build
WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

# Copy app source (includes .env.production if present)
COPY . .

# CRA/Vite will read .env.production automatically during build
RUN npm run build

# ---- Stage 2: Nginx runtime ----
FROM nginx:1.21.6-alpine
# needed for envsubst in entrypoint.sh
RUN apk add --no-cache gettext

COPY --from=build /app/build/ /usr/share/nginx/html/
COPY nginx/conf/nginx.conf.template /etc/nginx/conf.d/default.conf.template
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]