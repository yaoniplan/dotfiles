#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     # On iOS (a-Shell) environments, use the pure Python version instead:
#     # pip install opencc-python-reimplemented
#     "opencc>=1.4.1",
# ]
# ///
import sys
from opencc import OpenCC

def convert_to_traditional(simplified_text):
    # 's2t' converts Simplified Chinese to Traditional Chinese
    converter = OpenCC('s2t')
    return converter.convert(simplified_text)

# Check if a parameter was provided
if len(sys.argv) > 1:
    source_text = sys.argv[1]  # Get the first argument passed to the script
else:
    print("Please provide Simplified Chinese text as a parameter.")
    sys.exit(1)

# Convert and print the result without a trailing newline
traditional_text = convert_to_traditional(source_text)
print(traditional_text, end='')
