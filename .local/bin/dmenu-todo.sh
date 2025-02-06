#!/usr/bin/env bash

# Reference:
# https://tools.suckless.org/dmenu/scripts/todo

# Directory where the script is located
SCRIPT_DIR=$(dirname "$0")
file="$SCRIPT_DIR/todo.txt"

touch "$file"
height=$(wc -l "$file" | awk '{print $1}')
prompt="Add/delete a task: "

cmd=$(fuzzel --dmenu -l "$height" -p "$prompt" "$@" < "$file")
while [ -n "$cmd" ]; do
  if grep -q "^$cmd\$" "$file"; then
    grep -v "^$cmd\$" "$file" > "$file.$$"
    mv "$file.$$" "$file"
    height=$(( height - 1 ))
  else
    echo "$cmd" >> "$file"
    height=$(( height + 1 ))
  fi

  cmd=$(fuzzel --dmenu -l "$height" -p "$prompt" "$@" < "$file")
done

exit 0
