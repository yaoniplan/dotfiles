#!/usr/bin/env bash

slurp -p | grim -g - - | convert - txt: | awk 'NR==2 { print $3 }' | tee >(wl-copy) | xargs -I {} notify-send "{}"
