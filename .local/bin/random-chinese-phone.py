#!/usr/bin/env python3

import random


PREFIXES = [
    "130", "131", "132", "133", "134", "135", "136", "137", "138", "139",
    "150", "151", "152", "153", "155", "156", "157", "158", "159",
    "166", "167", "170", "171", "172", "173", "175", "176", "177", "178", "179",
    "180", "181", "182", "183", "184", "185", "186", "187", "188", "189",
    "191", "192", "193", "195", "196", "197", "198", "199",
]


def random_phone():
    prefix = random.choice(PREFIXES)
    suffix = "".join(random.choices("0123456789", k=8))
    return prefix + suffix


def main():
    print(random_phone())


if __name__ == "__main__":
    main()
