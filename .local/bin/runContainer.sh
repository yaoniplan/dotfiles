#!/usr//bin/env bash

# Set variables
yourImage="yaoniplan/note"
yourTag=$(date +%F) # (e.g. 2023-09-17)
yourPathIncludingDockerfile="~/note/"
yourPathIncludingDockerComposeYml="~/.config/note/"
yourLocalIPAddress="192.168.10.105"

# Determine whether it is on the local
if echo $(ip address) | grep --quiet "$yourLocalIPAddress"; then
    # Build and push the Docker image on the local
    docker build --tag "$yourImage":latest "$yourPathIncludingDockerfile" && \
    docker push "$yourImage":latest & \
    docker tag "$yourImage":latest "$yourImage":"$yourTag" && \
    docker push "$yourImage":"$yourTag"
    ssh yaoniplan 'bash -c "source ~/.local/bin/runContainer.sh"' &
else
    # Run the Docker container on the server
    cd "$yourPathIncludingDockerComposeYml" && docker-compose up --detach
fi
