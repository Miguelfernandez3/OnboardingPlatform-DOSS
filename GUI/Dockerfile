# Stage 1: build
FROM node:22-alpine AS build

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

ARG VITE_API_ADAPTER=doss
ARG VITE_API_BASE_URL=/api
ARG VITE_ENV=production

ENV VITE_API_ADAPTER=${VITE_API_ADAPTER} \
    VITE_API_BASE_URL=${VITE_API_BASE_URL} \
    VITE_ENV=${VITE_ENV}

RUN npm run build

# Stage 2: serve with nginx
FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 3001

CMD ["nginx", "-g", "daemon off;"]
