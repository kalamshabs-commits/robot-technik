#!/usr/bin/env bash
set -euo pipefail
mkdir -p robot-tech
JWT_SECRET=$(openssl rand -hex 32)
AES_KEY=$(openssl rand -hex 32)
cat > robot-tech/.env.server <<EOF
JWT_SECRET=$JWT_SECRET
AES_KEY=$AES_KEY
EOF
echo "Keys generated in robot-tech/.env.server"