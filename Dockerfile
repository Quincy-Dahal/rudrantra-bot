# Django + Ollama in one container.

FROM python:3.12-slim

# --- System dependencies ---
# curl: to download the Ollama binary directly (no systemd in a container,
#   so we skip Ollama's normal install script and just grab the binary).
# zstd: Ollama's current release archives are .tar.zst, not .tar.gz.
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    zstd \
    && rm -rf /var/lib/apt/lists/*

# --- Ollama itself ---
# Installed as a plain binary, not via ollama.com/install.sh, since that
# script assumes a systemd-managed host, not a container. This mirrors
# the extraction step that install.sh itself performs internally.
RUN curl -fsSL https://ollama.com/download/ollama-linux-amd64.tar.zst \
    | zstd -d | tar -xf - -C /usr

# --- Python dependencies ---
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- Application code ---
COPY . .

# --- Entrypoint ---
COPY entrypoint.sh /app/entrypoint.sh
RUN sed -i 's/\r$//' /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh


# Render sets $PORT at runtime and routes traffic to it - never hardcode
# a port here. Ollama's port (11434) is deliberately NOT exposed; it's
# only reachable from Django within this same container.
ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["/app/entrypoint.sh"]