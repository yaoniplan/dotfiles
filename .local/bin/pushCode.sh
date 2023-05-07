#!/usr/bin/env bash

# Set variables
repoDir="$HOME/note"
journalsDir="$repoDir/journals"
indexFile="$repoDir/index.html"
temporaryFile="$HOME/yaoniplan.md"

convertMarkdownToHtml() {
    # Generate Article
    cat $(ls -r "$journalsDir"/*.md) > "$temporaryFile"
    marked -i "$temporaryFile" -o "$indexFile" && rm "$temporaryFile"

    # Insert into the first line
    sed -i '1i\
<!DOCTYPE html>\
<html>\
<head>\
  <meta name="viewport" content="width=device-width, initial-scale=1">\
  <title>yaoniplan</title>\
  <link rel="stylesheet" href="assets/github-markdown-dark.css">\
  <style>\
    .markdown-body {\
      box-sizing: border-box;\
      min-width: 200px;\
      max-width: 980px;\
      margin: 0 auto;\
      padding: 45px;\
    }\
    @media (max-width: 767px) {\
      .markdown-body {\
        padding: 15px;\
      }\
    }\
  </style>\
</head>\
<body>\
  <article class="markdown-body">' "$indexFile"

    # Append to the last line
    echo "  </article>
</body>
</html>" >> "$indexFile"
}

# Push changes to master branch every odd day at 5pm
if [[ $(( $(date +%-j) % 2)) -eq 1 && $(date +%H:%M) == "17:00" ]]
then
    git -C "$repoDir" push origin development:master
fi

# Generate index.html file
convertMarkdownToHtml

# Commit and push changes to development branch
git -C "$repoDir" add --all
git -C "$repoDir" commit -m "Update at $(date +%F_%H-%M)"
git -C "$repoDir" push origin development
