#!/bin/sh

# Directory where the script is located
SCRIPT_DIR=$(dirname "$0")
GLYPH_LIST="$SCRIPT_DIR/.nerdfont.txt"

# Download nerdfont.txt if missing
if [ ! -e "$GLYPH_LIST" ]; then
  curl -s "https://raw.githubusercontent.com/8bitmcu/NerdFont-Cheat-Sheet/refs/heads/main/nerdfont.txt" > "$GLYPH_LIST"
fi

# Choose your Wayland menu (wofi, bemenu, or fuzzel)
LAUNCHER="fzf"
#LAUNCHER="fuzzel --dmenu -i -l 30"
# LAUNCHER="bemenu -i -l 30"
# LAUNCHER="fuzzel -d"

# Process the file and show selection
chosen=$(awk '{print $1 " nf-" $3 "-" $4}' "$GLYPH_LIST" | eval "$LAUNCHER" | awk '{print $1}')

# Exit if none chosen
[ -z "$chosen" ] && exit

# Handle insertion or clipboard copy
if [ -n "$1" ]; then
  wtype "$chosen"  # Requires wtype (alternative: ydotool)
else
  printf "%s" "$chosen" | wl-copy
  notify-send "Nerd Font Icon" "'$chosen' copied to clipboard!"
fi
