#!/bin/sh
set -eu
if [ ! -f /app/.env.server ]; then
  JWT_SECRET=$(openssl rand -hex 32)
  AES_KEY=$(openssl rand -hex 32)
  cat > /app/.env.server <<EOF
JWT_SECRET=$JWT_SECRET
AES_KEY=$AES_KEY
DATABASE_URL=${DATABASE_URL:-}
EOF
fi
set -a
. /app/.env.server || true
set +a
exec uvicorn cloud_api.ai_main:app --host 0.0.0.0 --port ${PORT:-8080}
