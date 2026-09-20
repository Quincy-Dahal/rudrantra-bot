#!/bin/sh
# entrypoint.sh
#
# Boot sequence for the combined Django + Ollama container:
#   1. Start Ollama in the background, bound to localhost only.
#   2. Wait until it actually responds (cold start takes a few seconds).
#   3. Pull the model if it isn't already present in this container.
#   4. Run Django migrations (safe to run on every boot - no-ops if
#      nothing's changed).
#   5. Start gunicorn in the foreground as the container's main process,
#      bound to 0.0.0.0:$PORT (Render supplies $PORT at runtime).
set -e

echo "Starting Ollama..."
OLLAMA_HOST=127.0.0.1:11434 ollama serve &

echo "Waiting for Ollama to become ready..."
until curl -s http://127.0.0.1:11434/api/tags > /dev/null; do
  sleep 1
done
echo "Ollama is up."

MODEL="${OLLAMA_MODEL:-qwen3:1.7b}"
echo "Ensuring model $MODEL is pulled..."
ollama pull "$MODEL"

echo "Running Django migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Starting gunicorn on port ${PORT:-8000}..."
exec gunicorn myproject.wsgi:application \
    --bind 0.0.0.0:"${PORT:-8000}" \
    --workers 2 \
    --timeout 120