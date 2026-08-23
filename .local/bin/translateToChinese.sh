#!/usr/bin/env bash

# This trans project is no longer maintained, and Google Search no longer works.
# Dependencies: fuzzel, trans, wl-clipboard, notify-send

# Check if the display server protocol is Wayland
if [[ "$XDG_SESSION_TYPE" = "wayland" ]]; then
    # Prompt user to input
    input="$(echo "" | fuzzel --dmenu)"

    # Check if input is empty
    if [[ -z "$input" ]]; then
        echo "Input is empty. Aborting."
        exit 1
    fi

    # Interact with user to select translation option
    selectedOption=$(echo -e "toEnglish\ntoChinese" | fuzzel --dmenu)

    case "$selectedOption" in
        "toEnglish")
            translationOption="-no-ansi -play -player mpg123"
            sourceLanguage="zh"
            targetLanguage="en"
            ;;
        "toChinese")
            translationOption="-no-ansi -speak -player mpg123"
            sourceLanguage="en"
            targetLanguage="zh"
            ;;
        *)
            echo "Invalid selection. Aborting."
            exit 1
            ;;
    esac

    # Translate text
    translation=$(trans $translationOption $sourceLanguage:$targetLanguage "$input")

    # Extract first and second paragraphs as translations
    firstParagraph=$(echo -e "$translation" | awk -v RS='' 'NR==1')
    secondParagraph=$(echo -e "$translation" | awk -v RS='' 'NR==2')

    if [[ "$selectedOption" == "toEnglish" ]]; then
        # Copy English translation to clipboard
        echo "$secondParagraph" | wl-copy
    else
        # Copy Chinese translation to clipboard
        echo "$firstParagraph" | wl-copy
    fi

    # Send a notification
    notify-send "$firstParagraph" "$secondParagraph"
else
    trans -player mpg123 :zh "$*" | less -R
fi
