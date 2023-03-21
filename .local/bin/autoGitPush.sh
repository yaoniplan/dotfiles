#!/usr/bin/env bash

now=$(date +%F_%T)
journalsDir=$HOME/note/journals
readmeFile=$HOME/note/.github/README.md

if [[ $(( $(date +%-j) % 2)) -eq 1 && $(date +%H:%M) == "17:00" ]]
then
    cd $HOME/note/
    git push origin development:master
fi

cd $HOME/note/
cat $(ls $journalsDir/*.md | sort -r) > $readmeFile
git add --all
git commit -m "Update at $now"
git push origin development
