#! /bin/sh

# Edit test script any where
# -e # Empty
targetFile=~/.local/bin/test.sh

if [[ $1 == "-e" ]]
then
    cat /dev/null > $targetFile
    vim $targetFile
else
    vim $targetFile
fi
