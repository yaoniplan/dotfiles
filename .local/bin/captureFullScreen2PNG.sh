#! /bin/sh

# Capture a window to PNG file

storageLocation=$HOME
fileName=$(date +%F_%H-%M.png)
sendToTheClipboard() {
    if command -v xclip &>/dev/null; then
        echo -n "![$fileName](../assets/$fileName)" | xclip -selection clipboard
    else
        echo -n "![$fileName](../assets/$fileName)" | xsel --input --clipboard
    fi
}

# Write a if condition judgement
if [ $1 == "full" ]; then
    scrot "$storageLocation"/"$fileName"
elif [ $1 == "focused" ]; then
    scrot --focused "$storageLocation"/"$fileName"
else
    scrot --select "$storageLocation"/"$fileName"
fi
sendToTheClipboard
