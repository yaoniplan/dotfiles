#!/usr/bin/env bash

notification () {
    notify-send "$notificationMessage" &

    for i in {1..2}
    do
        paplay "$audioFile"
    done
}

convertMarkdownToHeadOfHtml() {
    echo "<!DOCTYPE html>
<html>
<head>
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
  <title>yaoniplan</title>
  <link rel=\"stylesheet\" href=\"assets/github-markdown-dark.css\">
  <style>
    .markdown-body {
      box-sizing: border-box;
      min-width: 200px;
      max-width: 980px;
      margin: 0 auto;
      padding: 45px;
    }
    @media (max-width: 767px) {
      .markdown-body {
        padding: 15px;
      }
    }
  </style>
</head>
<body>
  <article class=\"markdown-body\">" > "$indexFile"
}

convertMarkdownToBodyOfHtml() {
    echo "  </article>
</body>
</html>" >> "$indexFile"
}

convertMarkdownToArticleOfHtml() {
    cat $(ls -r "$journalsDir"/*.md) > "$temporaryFile"
    marked -i "$temporaryFile" -o "$temporaryFile2"
    cat "$temporaryFile2" >> "$indexFile"
}
