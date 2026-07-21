FROM python:3.11-slim

# Create a non-root user
RUN useradd -u 1001 -m cabinops

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy only the backend code
COPY backend/ ./backend/

# Ensure the backend directory is writable by the non-root user for database and JSON files
RUN mkdir -p /app/backend/data && chown -R cabinops:cabinops /app/backend

# Switch to the non-root user
USER cabinops

EXPOSE 8000
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
