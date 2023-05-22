#!/usr/bin/env bash


# Push changes to master branch every odd day at 5pm
if [[ $(( $(date +%-j) % 2)) -eq 1 && $(date +%H:%M) == "17:00" ]]
then
    git -C "$repoDir" push origin development:master
fi

# Generate index.html file
convertMarkdownToHtml

# Commit and push changes to development branch
git -C "$repoDir" add --all
git -C "$repoDir" commit -m "Update at $(date +%F_%H-%M)"
git -C "$repoDir" push origin development
