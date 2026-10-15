#!/bin/env sh
qrencode --output=- "$(wl-paste)" | imv -
