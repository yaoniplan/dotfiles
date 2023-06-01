#!/usr/bin/env bash

# Dependencies: translate-shell

trans -player mpg123 :zh "$*" | less -R
