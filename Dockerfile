# ==========================================
# Stage 1: Build Frontend
# ==========================================
FROM node:20-alpine AS frontend-builder

WORKDIR /build

# Install frontend dependencies
COPY frontend/package*.json ./
RUN npm install

# Copy source and build static distribution
COPY frontend/ ./
RUN npm run build

# ==========================================
# Stage 2: Production Python Runtime
# ==========================================
FROM python:3.11-slim

# Set runtime environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Asia/Shanghai \
    PORT=8888 \
    HOST=0.0.0.0 \
    DATA_DIR=/app/data \
    DB_PATH=/app/data/lh.db \
    ADMIN_CONFIG_PATH=/app/data/admin_config.json \
    FRONTEND_DIST=/app/frontend/dist

# Install system dependencies, certificates and configure timezone
RUN apt-get update && \
    apt-get install -y --no-install-recommends tzdata ca-certificates curl && \
    ln -sf /usr/share/zoneinfo/${TZ} /etc/localtime && \
    echo "${TZ}" > /etc/timezone && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python backend dependencies
COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy backend application source code
COPY backend/ ./backend/

# Copy compiled frontend assets from Stage 1
COPY --from=frontend-builder /build/dist ./frontend/dist

# Create persistent storage volume mount point
RUN mkdir -p /app/data

# Declare volume for data persistence
VOLUME ["/app/data"]

# Expose default HTTP port
EXPOSE 8888

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8888/ || exit 1

# Set working directory to backend
WORKDIR /app/backend

# Start uvicorn server
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8888"]
