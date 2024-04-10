#!/usr/bin/env bash

# Dependencies: tofi, trans, wl-clipboard, notify-send

# Check if the display server protocol is Wayland
if [[ "$XDG_SESSION_TYPE" = "wayland" ]]; then
    # Prompt user to input
    input="$(echo "" | tofi)"

    # Check if input is empty
    if [[ -z "$input" ]]; then
        echo "Input is empty. Aborting."
        exit 1
    fi

    # Interact with user to select translation option
    selectedOption=$(echo -e "toEnglish\ntoChinese" | tofi)

    case "$selectedOption" in
        "toEnglish")
            translationOption="-no-ansi -play"
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

    # Copy Chinese translation to clipboard
    echo "$firstParagraph" | wl-copy

    # Send a notification
    notify-send "$firstParagraph" "$secondParagraph"
else
    trans -player mpg123 :zh "$*" | less -R
fi
