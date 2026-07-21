#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "opencc>=1.4.1",
# ]
# ///
import sys
from opencc import OpenCC

def convert_to_simplified(traditional_text):
    # 't2s' converts Traditional Chinese to Simplified Chinese
    converter = OpenCC('t2s')
    return converter.convert(traditional_text)

# Check if a parameter was provided
if len(sys.argv) > 1:
    source_text = sys.argv[1]  # Get the first argument passed to the script
else:
    print("Please provide Traditional Chinese text as a parameter.")
    sys.exit(1)

# Convert and print the result without a trailing newline
simplified_text = convert_to_simplified(source_text)
print(simplified_text, end='')
