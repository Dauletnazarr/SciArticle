#!/usr/bin/env bash
set -e
echo "Fixing ownership of /data for redisuser..."
chown -R redisuser:redisgroup /data || true

echo "Starting Redis as redisuser..."
exec su redisuser -c "redis-server --requirepass '$REDIS_PASSWORD'"
