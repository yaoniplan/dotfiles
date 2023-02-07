#! /bin/sh

# Generate random string
# At least one uppercase letter, one lowercase letter, one number, and one special symbol

generateRandomString=$(openssl rand -base64 $1)

echo $generateRandomString@gmail.com | xclip -selection clipboard
