# Python 3.12 Alpine für minimale Image-Größe und bessere Security
FROM python:3.12-alpine

# Set working directory
WORKDIR /app

# Accept build-time version and expose as environment
ARG APP_VERSION="dev-unknown"
ENV APP_VERSION=${APP_VERSION}

# Install build dependencies for Alpine
RUN apk add --no-cache gcc musl-dev

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Remove build dependencies to keep image small
RUN apk del gcc musl-dev

# Copy application code
COPY . .

# Create directory for SQLite databases
RUN mkdir -p tmp && chmod -R 777 tmp

# Expose port 8080 (consistent with app configuration)
EXPOSE 8080

# Start the application on port 8080
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]