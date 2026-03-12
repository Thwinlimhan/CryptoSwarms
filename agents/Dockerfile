FROM python:3.11-slim

WORKDIR /app

# Harden apt against transient Debian mirror/network issues during docker build.
RUN set -eux; \
    echo 'Acquire::Retries "8";' > /etc/apt/apt.conf.d/99-network-resilience; \
    echo 'Acquire::http::Timeout "30";' >> /etc/apt/apt.conf.d/99-network-resilience; \
    echo 'Acquire::https::Timeout "30";' >> /etc/apt/apt.conf.d/99-network-resilience; \
    echo 'Acquire::ForceIPv4 "true";' >> /etc/apt/apt.conf.d/99-network-resilience; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
      build-essential \
      curl \
      ca-certificates; \
    rm -rf /var/lib/apt/lists/*

# Copy pyproject.toml and README for dependency installation
COPY pyproject.toml README.md ./

# Install only core dependencies (backtest is optional and slow)
# To enable backtest features, change to: pip install --no-cache-dir .[backtest,memory]
RUN pip install --no-cache-dir .[memory]

# Copy the rest of the application code
COPY agents/ ./agents/
COPY api/ ./api/
COPY cryptoswarms/ ./cryptoswarms/
COPY memory/ ./memory/
COPY schemas/ ./schemas/

ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["python", "api/main.py"]
