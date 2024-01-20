#!/usr/bin/env bash

# Dependencies: wget, 7z or unzip, yt-dlp, ffmpeg

set -e # Exit immediately if a command exits with a non-zero status

URL="$@"
destinationDir="/mnt/yaoniplan/chinaMobile"

setProxy() {
    export http_proxy="100.80.81.110:7890"
    export https_proxy="100.80.81.110:7890"
    export no_proxy="localhost, 127.0.0.1"
}

unsetProxy() {
    unset http_proxy https_proxy no_proxy
}

if [[ -z "$URL" ]]; then
    echo "URL is empty. Downloading the latest China news by default."

    # Get the file name from URL
    #fileName=$(yt-dlp --get-filename --output "%(title)s.%(ext)s" --max-downloads 1 "https://www.ximalaya.com/album/31923706")

    # Download the file using yt-dlp
    yt-dlp --output "%(title)s.%(ext)s" --max-downloads 1 "https://www.ximalaya.com/album/31923706" && mv *.m4a /mnt/yaoniplan/chinaMobile/temporary/

    mv *.m4a /mnt/yaoniplan/chinaMobile/temporary/
    echo "Download completed!"
else
    echo "Failed to download the latest China news."
fi

if [[ $URL == *"github.com"* ]]; then
    if [[ $URL == *"releases/download"* ]]; then
        setProxy
	cd /mnt/yaoniplan/chinaMobile/
        wget "$URL"
	unsetProxy
	exit 0
    fi
    # Extract repository name from URL and use it as the file name
    fileName=$(basename "$URL" ".git")
    echo "Setting proxy..."
    setProxy
    echo "Downloading resources from GitHub..."
    wget --output-document=/mnt/yaoniplan/chinaMobile/"$fileName".zip "$URL"/archive/master.zip
    unsetProxy

    if [[ $? -eq 0 ]]; then
	echo "Download completed successfully. Extracting the download ZIP file..."
	if command -v 7z &>/dev/null; then
	    # Deal with the issue about garbled characters
	    yes Y | 7z x /mnt/yaoniplan/chinaMobile/"$fileName".zip -o/mnt/yaoniplan/chinaMobile/
        else
            unzip /mnt/yaoniplan/chinaMobile/"$fileName".zip -d /mnt/yaoniplan/chinaMobile/
	fi
	echo "Extraction completed!"

	echo "Deleting the file "$fileName".zip..."
        rm /mnt/yaoniplan/chinaMobile/"$fileName".zip
	echo "The ZIP file "$fileName".zip removed successfully."
    else
        echo "Failed to download the zip file."
    fi

elif [[ $URL == *"bilibili.com"* ]]; then
    echo "Downloading resources from BiliBili..."
    if command -v yt-dlp &>/dev/null; then
        unsetProxy # Unset proxy variables
	
	# Get the file name from URL
	fileName=$(yt-dlp --get-filename -o "%(title)s.%(ext)s" "$(echo "$URL" | sed 's/m.bilibili/www.bilibili/g')")

	# Download the file using yt-dlp
        yt-dlp -o "$fileName" "$(echo "$URL" | sed 's/m.bilibili/www.bilibili/g')"

	# Move the file to the target directory
        mv "$fileName" /mnt/yaoniplan/chinaMobile/

	echo "Download file "$fileName" completed!"
    else
        echo "Please install 'yt-dlp' to download files from BiliBili."
    fi

elif [[ $URL == *"youtube.com"* ]]; then
    echo "Setting proxy..."
    setProxy
    if command -v yt-dlp &>/dev/null; then
	# Get the file name from URL
	fileName=$(yt-dlp --get-filename -o "%(title)s.%(ext)s" "$(echo "$URL" | sed 's/m.youtube/www.youtube/g')")

	# Download the file using yt-dlp
    	echo "Downloading resources from YouTube..."
        yt-dlp -o "$fileName" "$(echo "$URL" | sed 's/m.youtube/www.youtube/g')"

	# Move the file to the target directory
        mv "$fileName" /mnt/yaoniplan/chinaMobile/

	echo "Download file "$fileName" completed!"
    else
        echo "Please install 'yt-dlp' to download files from YouTube."
    fi
elif [[ $URL == *"ankiweb.net"* ]]; then
    echo "Setting proxy..."
    setProxy
    if command -v wget &>/dev/null; then
	# Get the file name from URL
	fileName=$(date +%F_%H-%M-%S)

	# Download the file
    	echo "Downloading resources from AnkiWeb..."
	wget -P "$destinationDir" -O "$fileName".apkg "$URL"
	mv *.apkg "$destinationDir"
	#yt-dlp -P "$destinationDir"
	echo "Download file "$fileName" completed!"
    else
        echo "Please install 'wget' to download files from AnkiWeb."
    fi
elif [[ "$URL" == *"ximalaya.com"* ]]; then
    echo "Downloading resources from ximalaya..."
    yt-dlp --output "%(title)s.%(ext)s" "$URL"
    mv *.m4a "$destinationDir"
else
    #echo "URL is from other website. Skipping download."
    #echo "Downloading resources from other website..."
    #fileName=$(yt-dlp --get-filename -o "%(title)s.%(ext)s" "$URL")
    #yt-dlp --output "%(title)s.%(ext)s" "$URL"
    #mv "$fileName" "$destinationDir"
    ##mv *.m4a "$destinationDir"
    echo "Downloading resources from other website..."
    if command -v yt-dlp &>/dev/null; then
        unsetProxy # Unset proxy
	
	# Get the file name from URL
	fileName=$(yt-dlp --get-filename -o "%(title)s.%(ext)s" "$URL")

	# Download the file using yt-dlp
        yt-dlp -o "$fileName" "$URL"

	# Move the file to the target directory
        mv "$fileName" "$destinationDir"

	echo "Download file "$fileName" completed!"
    else
        echo "Please install 'yt-dlp' to download files from other website."
    fi
fi

unsetProxy # Unset proxy variables at the end of the script
