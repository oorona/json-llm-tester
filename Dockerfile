# Dockerfile

# --- Stage 1: Frontend Build ("frontend-builder") ---
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend

COPY frontend/package.json ./
# COPY frontend/package-lock.json ./  # MODIFICATION 1: Commented out
RUN npm install 

COPY frontend/ ./
RUN npm run build

# MODIFICATION 2a: Added to see build output
RUN echo "--- Contents of /app/frontend/dist (in frontend-builder stage) ---" && ls -R /app/frontend/dist 
# (Adjust /app/frontend/dist if your frontend build output directory is different)

# --- Stage 2: Backend Runtime / Final Image ---
FROM python:3.11-slim
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

COPY backend/requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY backend/.env /app/.env 
COPY backend/app ./app


RUN echo "--- Dockerfile: Contents of /app after .env and app code COPY ---" && ls -la /app/
RUN echo "--- Dockerfile: Contents of /app/app (should contain 'core') ---" && ls -la /app/app/
RUN echo "--- Dockerfile: Contents of /app/app/core (should contain 'config.py') ---" && ls -la /app/app/core/

# MODIFICATION 2b: Ensure source path here matches your actual frontend build output dir from Stage 1
COPY --from=frontend-builder /app/frontend/dist /app/static_frontend 

# MODIFICATION 2c: Added to see what was copied
RUN echo "--- Contents of /app/static_frontend (in final image) ---" && ls -R /app/static_frontend

EXPOSE 8000
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]