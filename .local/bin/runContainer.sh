#!/bin/bash

# Set variables
localIPAddress="192.168.10.105"
yourName="yaoniplan"
searchString="0.0.0.0:8000"
portInfo=$(docker ps --format "{{.Ports}}" | awk -F'->' '{print $1}')
containerID=$(docker ps --format "{{.ID}} {{.Ports}}" | awk '/'"$searchString"'/ {print $1}')

# Determine whether it is on the local
if echo $(ip address) | grep --quiet "$localIPAddress"; then
    # Push code to the server and run the container on it
    git -C $HOME/note add --all; git -C $HOME/note commit -m "Update at $(date +%F_%H-%M)"
    git -C $HOME/note push git@192.168.10.100:/var/git/note.git development
    ssh yaoniplan 'bash -c "source ~/.local/bin/runContainer.sh"' &
else
    # Determine if the container is running
    if echo "$portInfo" | grep --quiet "$searchString"; then
        docker stop "$containerID" && docker rm "$containerID"
    fi

    # Remove images with none and yourName tag
    docker images --filter "dangling=true" --quiet | xargs -r docker rmi --force
    docker images | awk '/'"$yourName"'/ {print $3}' | xargs -r docker rmi --force

    # Build the Docker image After pulling code
    if [[ -d $HOME/note/ ]]; then
        git -C $HOME/note/ pull origin development
    else
        git clone git@192.168.10.100:/var/git/note.git $HOME/note/
    fi
    docker build --tag "$yourName" $HOME/note/

    # Run the Docker container
    docker run --publish 8000:80 "$yourName" &
fi
