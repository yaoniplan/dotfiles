#!/usr/bin/env bash

if [[ $# -ne 0 ]]; then
    pactl set-sink-volume @DEFAULT_SINK@ "$@"%
else
    pactl set-sink-volume @DEFAULT_SINK@ 60%
fi
