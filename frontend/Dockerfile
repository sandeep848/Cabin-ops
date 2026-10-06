FROM node:22-alpine AS build
ARG PORTAL=passenger_screen
WORKDIR /app
COPY frontend/${PORTAL}/package*.json ./
RUN npm ci
COPY frontend/${PORTAL}/ ./
COPY frontend/shared/ /shared/
RUN npm run build
FROM nginxinc/nginx-unprivileged:stable-alpine
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 8080
