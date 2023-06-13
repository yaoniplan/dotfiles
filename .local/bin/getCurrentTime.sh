#!/usr/bin/env bash

# Dependencies: notify-send

export $(dbus-launch); notify-send "$(date)"
