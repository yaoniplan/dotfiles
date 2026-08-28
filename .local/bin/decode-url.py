#!/usr/bin/env python3

import sys
from urllib.parse import unquote


def main():
    if len(sys.argv) > 1:
        text = " ".join(sys.argv[1:])
    else:
        text = input("URL: ")

    print(unquote(text))


if __name__ == "__main__":
    main()
