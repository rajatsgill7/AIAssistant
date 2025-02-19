#!/bin/bash

# Define the network name
NETWORK_NAME="slot-wise-caller-agent-api-network"

# Get the current directory
CURRENT_DIR=$(pwd)

# List existing Docker networks
echo "Existing Docker networks:"
docker network ls

# Determine the correct Docker Compose command
if command -v docker-compose &> /dev/null; then
  DOCKER_COMPOSE="docker-compose"
elif command -v docker &> /dev/null && docker compose version &> /dev/null; then
  DOCKER_COMPOSE="docker compose"
else
  echo "Docker Compose is not installed."
  exit 1
fi

# Optionally remove the custom network if it exists and was created by the script
if docker network ls | grep -q "${NETWORK_NAME}"; then
  echo "Removing network ${NETWORK_NAME}..."
  docker network rm ${NETWORK_NAME}
  echo "Network ${NETWORK_NAME} removed."
else
  echo "Network ${NETWORK_NAME} does not exist or was not created by this script."
fi

echo "All services are stopped, and associated resources are removed."