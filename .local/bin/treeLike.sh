#! /bin/sh

# tree-like
find $1 | sort | sed "s;[^/]*/;|____;g" | sed "s;____|; |;g"
