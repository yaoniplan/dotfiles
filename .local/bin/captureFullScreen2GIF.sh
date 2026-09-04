#!/usr/bin/env bash

if [[ -n "$WAYLAND_DISPLAY" ]]; then
    # Wayland recording with wf-recorder
    getPIDOfRecorderProcess=$(pgrep -x wf-recorder)

    if [[ -n "$getPIDOfRecorderProcess" ]]; then
        # Stop recording
        kill -INT "$getPIDOfRecorderProcess"
        sleep 1  # Allow wf-recorder to finalize
        canberra-gtk-play -i complete
    else
        # Start recording
        fileName=$(date +%Y-%m-%dT%H:%M:%SZ).gif
        canberra-gtk-play -i camera-shutter
        wf-recorder -c gif -f "$HOME/$fileName" &
    fi
else
    source $HOME/.local/bin/master.sh

    # Delay before starting
    fileExtension="gif"
    DELAY=3

    # Duration and output file
    if [ $# -gt 0 ]; then
        D="--duration=$@"
    else
        echo Default recording duration "$DELAY"s to "$fileName".gif
        D="--duration=10 "$fileName".gif"
    fi
    XWININFO=$(xwininfo)
    read X <<< $(awk -F: '/Absolute upper-left X/{print $2}' <<< "$XWININFO")
    read Y <<< $(awk -F: '/Absolute upper-left Y/{print $2}' <<< "$XWININFO")
    read W <<< $(awk -F: '/Width/{print $2}' <<< "$XWININFO")
    read H <<< $(awk -F: '/Height/{print $2}' <<< "$XWININFO")

    echo Delaying $DELAY seconds. After that, byzanz will start
    for (( i=$DELAY; i>0; --i )) ; do
        echo $i
        sleep 1
    done

    byzanz-record --verbose --delay=0 --x=$X --y=$Y --width=$W --height=$H $D
    sendToTheClipboard
fi
