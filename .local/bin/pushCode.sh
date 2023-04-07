#!/usr/bin/env bash

# Set variables
repoDir="$HOME/note"
journalsDir="$repoDir/journals"
readmeFile="$repoDir/.github/README.md"

# Push changes to master branch every odd day at 5pm
if [[ $(( $(date +%-j) % 2)) -eq 1 && $(date +%H:%M) == "17:00" ]]
then
    git -C "$repoDir" push origin development:master
fi

# Concatenate all journals files and write to README file
cat $(ls "$journalsDir"/*.md | sort -r) > "$readmeFile"

# Commit and push changes to development branch
git -C "$repoDir" add --all
git -C "$repoDir" commit -m "Update at $(date +%F_%H-%M)"
git -C "$repoDir" push origin development
