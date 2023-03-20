#!/usr/bin/env bash

# Type "echo `date +%F_%T`" in terminal to display output
# Refer to https://unix.stackexchange.com/questions/395933/how-to-check-if-the-current-time-is-between-2300-and-0630

currentTime=$(date +%H:%M)
dayOfWeek=$(date +%u)
if (( ($dayOfWeek / 2) * 2 == $dayOfWeek ))
then
    cd $HOME/note/
    git push origin development:master
fi

cd $HOME/note/
cat $(ls /home/yaoniplan/note/journals/*.md | sort -r) > /home/yaoniplan/note/.github/README.md
git add --all
git commit -m "Update at `date +%F_%T`"
git push origin development
