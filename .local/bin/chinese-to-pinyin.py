#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "pypinyin>=0.55.0",
# ]
# ///

import sys
from pypinyin import pinyin, Style

def convert_to_pinyin_without_tones(chinese_text):
    # Convert Chinese text to Pinyin without tones
    return ''.join([item[0] for item in pinyin(chinese_text, style=Style.NORMAL)])

# Check if a parameter was provided
if len(sys.argv) > 1:
    product_name = sys.argv[1]  # Get the first argument passed to the script
else:
    print("Please provide a product name as a parameter.")
    sys.exit(1)  # Exit if no parameter is provided

# Convert the product name to Pinyin without tones
pinyin_without_tones = convert_to_pinyin_without_tones(product_name)

# Print the result
print(pinyin_without_tones, end='')
