#!/bin/bash

# Define the network name
NETWORK_NAME="slot-wise-caller-agent-api-network"

# Get the current directory
CURRENT_DIR=$(pwd)

# List existing Docker networks
echo "Existing Docker networks:"
docker network ls

# Check if the network already exists
if ! docker network ls | grep -q "${NETWORK_NAME}"; then
  echo "Network ${NETWORK_NAME} does not exist. Creating it..."
  docker network create ${NETWORK_NAME}
else
  echo "Network ${NETWORK_NAME} already exists."
fi

# Determine the correct Docker Compose command
if command -v docker-compose &> /dev/null; then
  DOCKER_COMPOSE="docker-compose"
elif command -v docker &> /dev/null && docker compose version &> /dev/null; then
  DOCKER_COMPOSE="docker compose"
else
  echo "Docker Compose is not installed."
  exit 1
fi

# Start services from the Docker Compose file in the current directory
echo "Starting services from ${CURRENT_DIR}/docker-compose.yml..."
${DOCKER_COMPOSE} -f "${CURRENT_DIR}/docker-compose.yml" up -d

echo "All services are up and running."