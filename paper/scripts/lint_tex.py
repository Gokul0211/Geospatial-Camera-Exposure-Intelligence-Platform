"""Cheap structural lint for the .tex sources (no LaTeX installation needed).

Checks brace balance and \\begin/\\end pairing. It does NOT replace compiling in Overleaf.
Run from the paper/ directory:  python scripts/lint_tex.py
"""
import glob
import re
from collections import Counter

BS = chr(92)  # backslash


def strip_comments(text: str) -> str:
    out = []
    for line in text.splitlines():
        i = 0
        while i < len(line):
            if line[i] == "%" and (i == 0 or line[i - 1] != BS):
                line = line[:i]
                break
            i += 1
        out.append(line)
    return "\n".join(out)


def brace_balance(text: str) -> int:
    text = text.replace(BS + "{", "").replace(BS + "}", "")
    depth = 0
    for ch in text:
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth < 0:
                return -1
    return depth


for path in sorted(glob.glob("figures/*.tex")) + ["main.tex"]:
    src = strip_comments(open(path, encoding="utf-8").read())
    begins = Counter(re.findall(BS + BS + "begin\\{([A-Za-z*]+)\\}", src))
    ends = Counter(re.findall(BS + BS + "end\\{([A-Za-z*]+)\\}", src))
    bal = brace_balance(src)
    print(f"{path:38s} braces={'OK' if bal == 0 else 'BAD(%d)' % bal}  envs={'OK' if begins == ends else 'MISMATCH'}")
