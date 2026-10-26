# Stage 1: build the React app
FROM node:20-alpine AS web
WORKDIR /web
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

# Stage 2: Python API that also serves the built React app
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend backend
COPY --from=web /web/dist frontend/dist
ENV PORT=8000
CMD uvicorn backend.app:app --host 0.0.0.0 --port $PORT
