#! /bin/sh

# Type "echo `date +%F_%T`" in terminal to display output
# Refer to https://unix.stackexchange.com/questions/395933/how-to-check-if-the-current-time-is-between-2300-and-0630

currentTime=$(date +%H:%M)
dayOfWeek=$(date +%A)
if [[ $dayOfWeek == "Monday" && $currentTime > "16:29" && $currentTime < "16:31" ]]
then
    cd $HOME/note/
    git add --all
    git commit -m "Update at `date +%F_%T`"
    git push
fi

cd $HOME/test/
git add --all
git commit -m "Update at `date +%F_%T`"
git push
