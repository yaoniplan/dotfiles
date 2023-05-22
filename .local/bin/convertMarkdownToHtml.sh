#!/usr/bin/env bash

source $HOME/.local/bin/master.sh

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
  <link rel="stylesheet" href="../assets/github-markdown-dark.css">\
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

# Generate index.html file
convertMarkdownToHtml
