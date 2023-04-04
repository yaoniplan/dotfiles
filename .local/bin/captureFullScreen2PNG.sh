#! /bin/sh

#Capture a window to PNG file

storageLocation=$HOME
fileName=$(date +%F_%H-%M.png)
sendToTheClipboard() {
    echo -n "![$fileName](../assets/$fileName)" | xclip -selection clipboard
}

# Write a if condition judgement
if [ $1 == "full" ]
then
    scrot "$HOME/$fileName"
else
    scrot -u "$HOME/$fileName"
fi
sendToTheClipboard
