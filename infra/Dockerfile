# Use an official Python runtime as a parent image
FROM python:3.13

# Prevent Python from writing pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies required by Poetry and some packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="/root/.local/bin:$PATH"

# Set the working directory
WORKDIR /app

# Copy only the files necessary for dependency installation
COPY pyproject.toml poetry.lock* /app/

# Install project dependencies using Poetry
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --no-root


# Copy the rest of the project
COPY . /app

# Default command (override via docker-compose for Celery worker, beat, etc.)
CMD ["bash"]

# Create a non-root user, e.g. 'celeryuser'
RUN useradd -ms /bin/bash celeryuser

# Switch to 'celeryuser'
USER celeryuser
