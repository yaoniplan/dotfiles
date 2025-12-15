#!/bin/sh

# Directory where the script is located
SCRIPT_DIR=$(dirname "$0")
WORD_LIST="$SCRIPT_DIR/google-10000-english.txt"

# Download the word list if missing
if [ ! -e "$WORD_LIST" ]; then
  curl -s "https://raw.githubusercontent.com/first20hours/google-10000-english/master/google-10000-english.txt" > "$WORD_LIST"
fi

# Choose your Wayland/X11 menu (dmenu, wofi, bemenu, fuzzel, etc)
LAUNCHER="tofi"
#LAUNCHER="fuzzel --dmenu -i -l 1"
# LAUNCHER="bemenu -i -l 20"
# LAUNCHER="wofi --dmenu"

# Pick a random word from the list
word=$(shuf -n 1 "$WORD_LIST")

# Show that word in dmenu (only one option)
chosen=$(printf "%s\n" "$word" | eval "$LAUNCHER")

# Exit if none chosen
[ -z "$chosen" ] && exit

# Handle insertion or clipboard copy
if [ -n "$1" ]; then
  # If an argument is passed, type the word (e.g. into a text field)
  wtype "$chosen"
else
  # Otherwise copy to clipboard and notify
  printf "%s" "$chosen" | wl-copy
  notify-send "Random Word" "'$chosen' copied to clipboard!" &
fi
