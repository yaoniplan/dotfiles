#! /bin/sh

# Type "echo `date +%F_%T`" in terminal to display output
# Refer to https://unix.stackexchange.com/questions/395933/how-to-check-if-the-current-time-is-between-2300-and-0630

currentTime=$(date +%H:%M)
dayOfWeek=$(date +%A)
if [[ $dayOfWeek == "Monday" && $currentTime > "16:59" && $currentTime < "17:01" ]]
then
    cd $HOME/note/
    git add --all
    git commit -m "Update at `date +%F_%T`"
    git push
fi

cd $HOME/test/
cat $(ls /home/yaoniplan/test/journals/*.md | sort -r) > /home/yaoniplan/test/.github/README.md
git add --all
git commit -m "Update at `date +%F_%T`"
git push
