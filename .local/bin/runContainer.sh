#!/bin/bash

# Set variables
localIPAddress="192.168.10.105"
yourName="yaoniplan"
searchString="0.0.0.0:8000"
portInfo=$(docker ps --format "{{.Ports}}" | awk -F'->' '{print $1}')
containerID=$(docker ps --format "{{.ID}} {{.Ports}}" | awk '/'"$searchString"'/ {print $1}')

if echo $(ip address) | grep --quiet "$localIPAddress"; then
    ssh yaoniplan 'bash -c "source ~/.local/bin/runContainer.sh"' &
else
    # Determine if the container is running or not
    if echo "$portInfo" | grep --quiet "$searchString"; then
        docker stop "$containerID"
    fi

    # Remove images with none and yourName tag
    docker images --filter "dangling=true" --quiet | xargs -r docker rmi --force
    docker images | awk '/'"$yourName"'/ {print $3}' | xargs -r docker rm --force

    # Build the Docker image
    docker build --tag "$yourName" ~/note/

    # Run the Docker container
    docker run --publish 8000:80 "$yourName" &
fi
