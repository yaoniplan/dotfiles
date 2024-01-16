#!/usr/bin/env bash

# Set variables
yourImage="yaoniplan/note"
yourTag=$(date +%F) # (e.g. 2023-09-17)
yourPathIncludingDockerfile="$HOME/note"
yourPathIncludingDockerComposeYml="$HOME/.config/note"
yourLocalIPAddress="100.80.81.110"
yourServerAlias="server"

# Remove existing runing containers
docker ps | grep "$yourImage" | awk '{print $1}' | xargs -r docker stop {} && docker rm {}

# Remove images with none and yourName tag
docker images --filter "dangling=true" --quiet | xargs -r docker rmi --force
docker images | grep "$yourImage" | awk '{print $3}' | xargs -r docker rmi --force

# Determine whether it is on the local
if echo $(ip address) | grep --quiet "$yourLocalIPAddress"; then
    # Build and push the Docker image on the local
    docker build --tag "$yourImage":latest "$yourPathIncludingDockerfile"
    docker push "$yourImage":latest
    docker tag "$yourImage":latest "$yourImage":"$yourTag" && \
    docker push "$yourImage":"$yourTag" &
    ssh "$yourServerAlias" 'bash -c "source ~/.local/bin/runContainer.sh"'
else
    # Run the Docker container on the server
    if [[ -x /usr/bin/docker-compose ]]; then
        cd "$yourPathIncludingDockerComposeYml"/ && /usr/bin/docker-compose up --detach
    elif [[ -x $HOME/.nix-profile/bin/docker-compose ]]; then
        # Maybe using the package manager "Nix"
        cd "$yourPathIncludingDockerComposeYml"/ && $HOME/.nix-profile/bin/docker-compose up --detach
    else
        echo "docker-compose command not found"
    fi
fi
