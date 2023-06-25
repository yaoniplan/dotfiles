#!/bin/bash

#Set variables
yourName="yaoniplan"
searchString="0.0.0.0:8000"
portInfo=$(docker ps --format "{{.Ports}}" | awk -F'->' '{print $1}')
containerID=$(docker ps --format "{{.ID}} {{.Ports}}" | awk '/'"$searchString"'/ {print $1}')

# Check if search string is in port info
if echo "$portInfo" | grep --quiet "$searchString"; then
    docker stop "$containerID"
fi

# Determin if the container is running or not
# Remove images with none tag
docker images --filter "dangling=true" --quiet | xargs -r docker rmi --force

# Build the Docker image
docker build --tag "$yourName" ~/note/

# Run the Docker container
docker run --publish 8000:80 "$yourName" &
