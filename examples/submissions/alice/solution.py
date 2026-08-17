"""Example submission."""

import sys


def add(left: int, right: int) -> int:
    return left + right


if __name__ == "__main__":
    if len(sys.argv) == 3:
        print(add(int(sys.argv[1]), int(sys.argv[2])))

