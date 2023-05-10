#!/usr/bin/env bash

redshift -O 1500 &>/dev/null &
clash &>/dev/null &
rclone mount aliyundrive:/ /mnt/aliyundrive/ &>/dev/null &
