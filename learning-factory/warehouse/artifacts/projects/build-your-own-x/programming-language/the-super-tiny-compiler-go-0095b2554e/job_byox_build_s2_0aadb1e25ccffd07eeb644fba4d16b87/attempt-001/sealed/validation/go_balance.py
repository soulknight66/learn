#!/usr/bin/env python3
"""Lexically check delimiter balance in Go files when gofmt is unavailable."""

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PAIRS = {")": "(", "]": "[", "}": "{"}


def problem(source):
    stack = []
    index = 0
    line = 1
    while index < len(source):
        char = source[index]
        if char == "\n":
            line += 1
            index += 1
            continue
        if source.startswith("//", index):
            end = source.find("\n", index)
            index = len(source) if end < 0 else end
            continue
        if source.startswith("/*", index):
            end = source.find("*/", index + 2)
            if end < 0:
                return f"unclosed block comment at line {line}"
            line += source[index : end + 2].count("\n")
            index = end + 2
            continue
        if char in ('"', "'", "`"):
            quote = char
            start_line = line
            index += 1
            while index < len(source):
                if source[index] == "\n":
                    line += 1
                if quote != "`" and source[index] == "\\":
                    index += 2
                    continue
                if index < len(source) and source[index] == quote:
                    index += 1
                    break
                index += 1
            else:
                return f"unclosed {quote} literal at line {start_line}"
            continue
        if char in "([{":
            stack.append((char, line))
        elif char in ")]}":
            if not stack or stack[-1][0] != PAIRS[char]:
                return f"unmatched {char} at line {line}"
            stack.pop()
        index += 1
    if stack:
        return f"unclosed {stack[-1][0]} at line {stack[-1][1]}"
    return None


def main():
    files = sorted(ROOT.rglob("*.go"))
    failures = []
    for path in files:
        issue = problem(path.read_text(encoding="utf-8"))
        if issue:
            failures.append(f"{path.relative_to(ROOT)}: {issue}")
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print("go-lexical-balance: OK")
    print(f"go-source-files: {len(files)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
