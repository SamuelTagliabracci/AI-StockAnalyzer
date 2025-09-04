# Dockerfile for TSX Stock Analyzer
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories with proper permissions
RUN mkdir -p logs data backups temp && \
    chmod 755 logs data backups temp

# Create a non-root user for security
RUN useradd --create-home --shell /bin/bash tsx_user && \
    chown -R tsx_user:tsx_user /app

# Switch to non-root user
USER tsx_user

# Expose port
EXPOSE 5000

# Set environment variables
ENV FLASK_ENV=production
ENV HOST=0.0.0.0
ENV PORT=5000
ENV DATABASE_PATH=/app/data/tsx_analyzer.db
ENV LOG_FILE=/app/logs/tsx_analyzer.log

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/api/stats || exit 1

# Run the application
CMD ["python", "run.py", "--host", "0.0.0.0", "--port", "5000"]