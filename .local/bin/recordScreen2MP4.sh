#!/usr/bin/env bash

# Set variables
setFileName=$(date +%F_%H-%M)
setFrameRate="30"  # 30 fps for smaller files
screenResolution="1366x768"  # Adjust as needed
bitrate="1500k"  # Target bitrate for smaller files
tempFile="$HOME/temp_$setFileName.mp4"  # Temporary file path
outputFile="$HOME/$setFileName.mp4"  # Final MP4 output path
gifFile="$HOME/$setFileName.gif"  # Final GIF output path

# Function to trim the last second of the recording
trim_last_second() {
    if [[ -f "$tempFile" ]]; then
        duration=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$tempFile" 2>/dev/null)
        if [[ -z "$duration" || ! "$duration" =~ ^[0-9]+(\.[0-9]+)?$ ]]; then
            echo "Error: Could not get valid duration from $tempFile"
            rm -f "$tempFile"
            exit 1
        fi
        trimDuration=$(awk "BEGIN {print $duration - 1}")
        if (( $(echo "$trimDuration > 0" | bc -l) )); then
            ffmpeg -i "$tempFile" -t "$trimDuration" -c:v copy -c:a copy -y "$outputFile" 2>/dev/null || {
                echo "Trimming failed."
                rm -f "$tempFile"
                exit 1
            }
            rm -f "$tempFile"
        else
            echo "Error: Recording too short to trim 1 second."
            rm -f "$tempFile"
            exit 1
        fi
    else
        echo "Error: Temporary file $tempFile not found."
        exit 1
    fi
}

# Function to convert MP4 to GIF
convert_to_gif() {
    # Generate a palette from the video
    ffmpeg -y -i "$outputFile" -vf fps=10,scale=640:-1:flags=lanczos,palettegen "$HOME/palette.png" 2>/dev/null

    # Use the palette to create the GIF
    ffmpeg -y -i "$outputFile" -i "$HOME/palette.png" -filter_complex \
      "fps=10,scale=640:-1:flags=lanczos[x];[x][1:v]paletteuse" \
      "$gifFile" 2>/dev/null

    # Remove the temporary palette file
    rm -f "$HOME/palette.png"
}

# Check if running Wayland or X11
if [[ -n "$WAYLAND_DISPLAY" ]]; then
    # Wayland recording with wf-recorder
    getPIDOfRecorderProcess=$(pgrep -f "wf-recorder")
    if [[ -n "$getPIDOfRecorderProcess" ]]; then
        # Stop recording
        kill "$getPIDOfRecorderProcess"
        sleep 1  # Allow wf-recorder to finalize
        trim_last_second
        convert_to_gif
    else
        # Start recording
        wf-recorder -g "$screenResolution+0,0" -c libx264 -r "$setFrameRate" --bitrate "$bitrate" --profile main -f "$tempFile" || {
            echo "Recording failed. Ensure wf-recorder is installed and Wayland supports screen capture."
            rm -f "$tempFile"
            exit 1
        }
    fi
elif [[ -n "$DISPLAY" ]]; then
    # X11 recording with ffmpeg x11grab
    getScreenResolution=$(xdpyinfo | grep dimensions | awk '{print $2}')
    getPIDOfFfmpegProcess=$(pgrep -f "ffmpeg -f x11grab")
    if [[ -n "$getPIDOfFfmpegProcess" ]]; then
        # Stop recording
        kill -SIGINT "$getPIDOfFfmpegProcess"
        sleep 1  # Allow ffmpeg to finalize
        trim_last_second
        convert_to_gif
    else
        # Start recording
        ffmpeg -f x11grab -video_size "$getScreenResolution" -framerate "$setFrameRate" -i :0.0 -c:v libx264 -b:v "$bitrate" -profile:v main "$tempFile" || {
            echo "Recording failed. Check ffmpeg and X11 setup."
            rm -f "$tempFile"
            exit 1
        }
    fi
else
    echo "Error: Neither Wayland nor X11 session detected."
    exit 1
fi
