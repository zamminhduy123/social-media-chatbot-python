# Use Python 3.12 slim image for a smaller footprint
FROM python:3.12-slim

# Set the working directory inside the container
WORKDIR /app

# Install system dependencies required for some Python packages (like ChromaDB)
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv from the official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy pyproject.toml to leverage Docker cache
COPY pyproject.toml .

# Install Python dependencies using uv
# --system: installs into the system Python environment (no virtualenv needed in Docker)
# --no-cache: keeps the image size down
RUN uv pip install --system --no-cache -r pyproject.toml

# Copy the rest of the application code
COPY . .

# Expose the port the app runs on
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "app_fastapi:app", "--host", "0.0.0.0", "--port", "8000"]