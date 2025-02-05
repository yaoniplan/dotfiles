#!/usr/bin/env sh

if [[ "$#" -ne 0 ]]; then
    myProject="$@"
else
    read -p "Enter your project name (e.g. store): " myProject
fi

remote="/home/yaoniplan/.config/$myProject"
local="/home/yaoniplan/.config/$myProject"

selectedOption=$(echo -e "toLocal\ntoRemote" | tofi)

case "$selectedOption" in
    "toLocal")
        option="yaoniplan@100.65.173.16:$remote $local"
        ;;
    "toRemote")
        option="$local yaoniplan@100.80.81.110:$remote"
        ;;
    *)
        echo "Invalid selection. Aborting."
        exit 1
        ;;
esac

eval rsync -av "$option"
