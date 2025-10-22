FROM python:3.14-slim

# Accept build arguments for user/group IDs (optional, for matching host user)
ARG USER_ID=1000
ARG GROUP_ID=1000

# Create a non-root user with specified UID/GID
RUN groupadd -r -g ${GROUP_ID} appuser && \
    useradd -r -u ${USER_ID} -g appuser appuser

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directory for persistent storage
RUN mkdir -p /app/data

# Change ownership to non-root user
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Run the application
CMD ["python", "app.py"]
