#!/usr/bin/env bash

# Set variables
repoDir="$HOME/note"
journalsDir="$repoDir/journals"
indexFile="$repoDir/index.html"
temporaryFile="/tmp/yaoniplan.txt"
temporaryFile2="/tmp/yaoniplan2.txt"

# Push changes to master branch every odd day at 5pm
if [[ $(( $(date +%-j) % 2)) -eq 1 && $(date +%H:%M) == "17:00" ]]
then
    git -C "$repoDir" push origin development:master
fi

# Generate index.html file
source master.sh
convertMarkdownToHeadOfHtml
convertMarkdownToArticleOfHtml
convertMarkdownToBodyOfHtml

# Commit and push changes to development branch
git -C "$repoDir" add --all
git -C "$repoDir" commit -m "Update at $(date +%F_%H-%M)"
git -C "$repoDir" push origin development
