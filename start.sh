#!/bin/bash

set -e
set -o pipefail

PROJECT_NAME="scisource_local"
ENV_FILE="infra/.env"
DOCKER_COMPOSE_FILE="infra/docker-compose.yml"
PYTHON_SCRIPT="run_polling.py"

docker compose -p $PROJECT_NAME --env-file $ENV_FILE -f $DOCKER_COMPOSE_FILE up --build -d

sleep 5

python3 $PYTHON_SCRIPT
