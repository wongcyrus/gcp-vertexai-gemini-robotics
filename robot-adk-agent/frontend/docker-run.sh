#!/bin/bash

# Build and run the frontend webapp Docker container

set -e

IMAGE_NAME="frontend-webapp"
CONTAINER_NAME="frontend-webapp-container"
PORT=3000

echo "Building Docker image..."
docker build -t $IMAGE_NAME .

echo "Stopping existing container if running..."
docker stop $CONTAINER_NAME 2>/dev/null || true
docker rm $CONTAINER_NAME 2>/dev/null || true

echo "Running new container..."
docker run -d \
    --name $CONTAINER_NAME \
    -p $PORT:80 \
    $IMAGE_NAME

echo "Frontend webapp is now running at http://localhost:$PORT"
echo "Container name: $CONTAINER_NAME"
echo ""
echo "To view logs: docker logs $CONTAINER_NAME"
echo "To stop: docker stop $CONTAINER_NAME"
