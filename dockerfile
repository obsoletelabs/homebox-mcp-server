# ---- Build stage ----
FROM python:3.12 AS builder

WORKDIR /app



# Install dependencies into a virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ---- Runtime stage ----
FROM python:3.12-slim

WORKDIR /app

# Install Caddy
RUN apt-get update && apt-get install -y --no-install-recommends caddy \
    && rm -rf /var/lib/apt/lists/*

# Add Caddy config
COPY ./src/Caddyfile /etc/caddy/Caddyfile

# Copy the venv from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application source
COPY ./src .

# Non-root user for security
RUN adduser --disabled-password --gecos "" appuser
USER appuser

EXPOSE 8000

# Run both MCP server + Caddy
CMD ["sh", "-c", "python main.py & caddy run --config /etc/caddy/Caddyfile"]
