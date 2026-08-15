#!/usr/bin/env bash

# Source your custom functions or environment variables
#source $HOME/.local/bin/master.sh

# Define the repository directory
repoDir="$HOME/.config/note"  # Update this with your actual repo path

# Check if a commit has already been made today
today=$(date +%F)
last_commit_date=$(git -C "$repoDir" log -1 --format=%cd --date=short)

# Push changes to development branch
if [[ "$last_commit_date" == "$today" ]]; then
    # Generate index.html file
    #source $HOME/.local/bin/convertMarkdownToHtml.sh

    # Amend the last commit instead of creating a new one
    git -C "$repoDir" add --all
    git -C "$repoDir" commit --amend --no-edit -m "Update at $(date +%F_%H-%M)"
    # Push changes to development branch
    git -C "$repoDir" push origin development --force
else
    # Push changes to master branch
    git -C "$repoDir" push origin development:master

    # Generate index.html file
    #source $HOME/.local/bin/convertMarkdownToHtml.sh

    # Create a new commit if no commits were made today
    git -C "$repoDir" add --all
    git -C "$repoDir" commit -m "Update at $(date +%F_%H-%M)"

    # Push changes to development branch
    git -C "$repoDir" push origin development
fi
