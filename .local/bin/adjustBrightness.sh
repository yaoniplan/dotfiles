#!/usr/bin/env bash

#Dependencies: brightnessctl

if [[ $# -ne 0 ]]; then
    brightnessctl set "$@"%
else
    brightnessctl set 20%
fi
