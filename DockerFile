# Use Playwright's official Python image (includes browsers & dependencies)
FROM mcr.microsoft.com/playwright/python:latest

# Create app directory
WORKDIR /usr/src/app

# Upgrade pip and install poetry (or use pip if you prefer)
RUN python -m pip install --upgrade pip
RUN pip install poetry

# Copy dependency metadata first for layer caching
COPY pyproject.toml poetry.lock* /usr/src/app/

# Configure poetry to not create virtualenvs (so dependencies are available in container)
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi

# Copy the rest of the application code
COPY . /usr/src/app

# Ensure Playwright browsers path is set (optional; base image already contains browsers)
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# Expose port (match your FastAPI port, Render may provide $PORT at runtime)
EXPOSE 10000

# Run uvicorn (use the same module path as your project)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "10000", "--proxy-headers"]
