#!/usr/bin/env python3
"""Stamp the canonical site header into hand-maintained pages.

The header's single source of truth is _partials/site-header.html (markup +
behavior) and _partials/site-header.css (all header styling, including the
First-principles dropdown that makes the Operating Envelope discoverable).
This script renders those partials into the delimited regions of each target:

  <!-- SITE-HEADER:BEGIN --> ... <!-- SITE-HEADER:END -->
  /* SITE-HEADER-CSS:BEGIN */ ... /* SITE-HEADER-CSS:END */

Targets (path relative to the portfolio root, fragment-link prefix):
  index.src.html                                  prefix ""
  first-principles/index.html                     prefix "/portfolio"
  first-principles/operating-envelope/index.html  prefix "/portfolio"

build.py reads the same partials at build time for the feed and per-post
pages, so every page on the site carries the identical header.

Usage: python3 stamp-header.py [--check]
  --check: report drift and exit 1 without writing anything.
"""

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PARTIALS = HERE / "_partials"

TARGETS = [
    ("index.src.html", ""),
    ("first-principles/index.html", "/portfolio"),
    ("first-principles/operating-envelope/index.html", "/portfolio"),
]

HEADER_BEGIN = "<!-- SITE-HEADER:BEGIN -->"
HEADER_END = "<!-- SITE-HEADER:END -->"
CSS_BEGIN = "/* SITE-HEADER-CSS:BEGIN */"
CSS_END = "/* SITE-HEADER-CSS:END */"


def render_header(prefix):
    return (PARTIALS / "site-header.html").read_text(encoding="utf-8").replace(
        "{{PREFIX}}", prefix
    )


def render_css():
    return (PARTIALS / "site-header.css").read_text(encoding="utf-8")


def stamp_region(text, begin, end, rendered):
    pattern = re.compile(re.escape(begin) + r".*?" + re.escape(end), re.S)
    replacement = begin + "\n" + rendered.rstrip("\n") + "\n" + end
    new, n = pattern.subn(replacement, text)
    if n != 1:
        raise SystemExit(f"expected exactly one stamped region {begin}, found {n}")
    return new


def stamp_text(text, prefix):
    text = stamp_region(text, HEADER_BEGIN, HEADER_END, render_header(prefix))
    text = stamp_region(text, CSS_BEGIN, CSS_END, render_css())
    return text


def main():
    check = "--check" in sys.argv[1:]
    dirty = []
    for rel, prefix in TARGETS:
        p = HERE / rel
        text = p.read_text(encoding="utf-8")
        try:
            new = stamp_text(text, prefix)
        except SystemExit as e:
            print(f"{rel}: {e}")
            return 2
        if new != text:
            dirty.append(rel)
            if not check:
                p.write_text(new, encoding="utf-8")
    if dirty:
        print(("DRIFT: " if check else "STAMPED: ") + ", ".join(dirty))
        return 1 if check else 0
    print("site header in sync on all targets")
    return 0


if __name__ == "__main__":
    sys.exit(main())
