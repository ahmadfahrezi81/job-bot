# FROM python:3.11-slim

# ENV DEBIAN_FRONTEND=noninteractive
# ENV PYTHONUNBUFFERED=1
# ENV UV_CACHE_DIR=/root/.cache/uv

# # Install system packages for Playwright
# RUN apt-get update && apt-get install -y --no-install-recommends \
#     ca-certificates \
#     curl \
#     git \
#     build-essential \
#     wget \
#     libnss3 \
#     libatk1.0-0 \
#     libatk-bridge2.0-0 \
#     libcups2 \
#     libx11-6 \
#     libxcomposite1 \
#     libxdamage1 \
#     libxrandr2 \
#     libgbm1 \
#     libasound2 \
#     libpangocairo-1.0-0 \
#     libgtk-3-0 \
#     libxss1 \
#     libglib2.0-0 \
#     libx11-xcb1 \
#     libxcb1 \
#     libdrm2 \
#     libexpat1 \
#     libfontconfig1 \
#     libpango-1.0-0 \
#     && rm -rf /var/lib/apt/lists/*

# # Install uv
# RUN pip install uv

# WORKDIR /usr/src/app

# # Copy dependencies and install (✅ include lock file)
# COPY pyproject.toml uv.lock /usr/src/app/
# RUN uv sync --frozen --no-dev

# # Copy source code
# COPY . /usr/src/app

# # Install Playwright browsers
# RUN uv run playwright install chromium

# EXPOSE 10000

# CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "10000"]


# =========================
# Stage 1: Builder
# Full environment for compilation
# =========================
FROM python:3.11-slim AS builder

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV UV_CACHE_DIR=/root/.cache/uv

# Install system packages for Playwright & LaTeX
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    git \
    build-essential \
    wget \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libx11-6 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpangocairo-1.0-0 \
    libgtk-3-0 \
    libxss1 \
    libglib2.0-0 \
    libx11-xcb1 \
    libxcb1 \
    libdrm2 \
    libexpat1 \
    libfontconfig1 \
    libpango-1.0-0 \
    texlive-latex-base \
    texlive-latex-recommended \
    texlive-fonts-recommended \
    texlive-latex-extra \
    latexmk \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

WORKDIR /usr/src/app

# Copy dependencies and install
COPY pyproject.toml uv.lock /usr/src/app/
RUN uv sync --frozen --no-dev

# Copy source code
COPY . /usr/src/app

# Install Playwright browsers
RUN uv run playwright install chromium

# =========================
# Stage 2: Runtime
# Only runtime dependencies (smaller)
# =========================
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
ENV UV_CACHE_DIR=/root/.cache/uv

WORKDIR /usr/src/app

# Copy Python environment from builder
COPY --from=builder /root/.cache/uv /root/.cache/uv
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin/uv /usr/local/bin/uv

# Copy Playwright browser binaries
COPY --from=builder /root/.cache/ms-playwright /root/.cache/ms-playwright

# Copy source code
COPY --from=builder /usr/src/app /usr/src/app

# Copy LaTeX runtime (needed for PDF compilation)
COPY --from=builder /usr/share/texlive /usr/share/texlive
COPY --from=builder /usr/share/texmf /usr/share/texmf

EXPOSE 10000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "10000"]
