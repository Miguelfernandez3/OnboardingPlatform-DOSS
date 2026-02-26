FROM node:22-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

ARG VITE_API_ADAPTER=doss
ARG VITE_API_BASE_URL=http://localhost:4321/api
ARG VITE_ENV=production

ENV VITE_API_ADAPTER=${VITE_API_ADAPTER} \
    VITE_API_BASE_URL=${VITE_API_BASE_URL} \
    VITE_ENV=${VITE_ENV}

RUN npm run build

EXPOSE 3001

CMD ["npm", "run", "preview", "--", "--host", "0.0.0.0", "--port", "3001"]
