#!/usr//bin/env bash

# Set variables
yourName="yaoniplan"
yourImage="yaoniplan/note"
yourTag=$(date +%F) # (e.g. 2023-09-17)
yourPathIncludingDockerfile="$HOME/note"
yourPathIncludingDockerComposeYml="$HOME/.config/note"

# Remove existing runing containers
docker ps --format "{{.ID}} {{.Image}}" | awk '/'"yaoniplan"'/ {print $1}' | xargs -r docker stop {} && docker rm {}

# Remove images with none and yourName tag
docker images --filter "dangling=true" --quiet | xargs -r docker rmi --force
docker images | awk '/'"$yourName"'/ {print $3}' | xargs -r docker rmi --force

# Determine whether it is on the local
if echo $(ip address) | grep --quiet "$yourLocalIPAddress"; then
    # Build and push the Docker image on the local
    docker build --tag "$yourImage":latest "$yourPathIncludingDockerfile"
    docker push "$yourImage":latest
    docker tag "$yourImage":latest "$yourImage":"$yourTag" && \
    docker push "$yourImage":"$yourTag" &
    ssh yaoniplan 'bash -c "source ~/.local/bin/runContainer.sh"' &
else
    # Run the Docker container on the server
    cd "$yourPathIncludingDockerComposeYml" && docker-compose up --detach
fi
