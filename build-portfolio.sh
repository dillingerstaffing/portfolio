#!/usr/bin/env bash
# Build, verify, commit, and push the portfolio site.
# Usage: build-portfolio.sh "commit message"
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "usage: build-portfolio.sh \"commit message\"" >&2
  exit 1
fi

cd "$(dirname "$0")"

echo "==> building index.html from data/*.json"
python3 build.py

echo "==> verifying generated output"
python3 - << 'EOF'
import json
page = open('index.html', encoding='utf-8').read()
data_js = open('cards-data.js', encoding='utf-8').read()
cards = json.load(open('data/cards.json'))
chips = {c['key']: c for c in json.load(open('data/chips.json'))}
assert json.dumps(cards, ensure_ascii=False, separators=(",", ":")) in data_js, "baked cards JSON missing from cards-data.js"
assert json.dumps(chips, ensure_ascii=False, separators=(",", ":")) in data_js, "baked chips JSON missing from cards-data.js"
assert '<script src="cards-data.js"></script>' in page, "cards-data.js script tag missing from page"
assert 'window.__PROJECTS__ =' not in page, "card payload should not be inline in page"
# The app script reads these globals: a missing declaration is a runtime
# ReferenceError that node --check cannot catch (it killed card rendering
# once). Fail the build instead.
for g in ('window.__PROJECTS__', 'window.__CHIPS_BY_KEY__', 'window.__WIGMORE__'):
    assert (g + ' =') in data_js, f"{g} not assigned in cards-data.js"
for decl in ('const PROJECTS = window.__PROJECTS__;',
             'const CHIPS_BY_KEY = window.__CHIPS_BY_KEY__;',
             'const WIGMORE = window.__WIGMORE__;'):
    assert decl in page, f"app script missing declaration: {decl}"
strips = page.count('class="layer-strip"') + page.count('class=\\"layer-strip\\"')
ports = page.count('class="portability"') + page.count('class=\\"portability\\"')
print(f"cards: {len(cards)} (want 140)")
print(f"layer-strip markers (static article strips + JS card renderer): {strips}")
print(f"portability markers (JS renderer): {ports}")
for p in ("__PROJECTS_JSON__", "__CHIPS_JSON__", "__WIGMORE_JSON__", "LAYER-STRIP:"):
    assert p not in page, f"unresolved placeholder: {p}"
print("no unresolved placeholders")
EOF

echo "==> committing and pushing"
git add data/cards.json data/articles.json data/chips.json data/isa-decisions.json data/wigmore.json data/feed.json index.src.html index.html cards-data.js build.py build-portfolio.sh BUILD.md drift-gate.py sitemap.xml og-image.png robots.txt llms.txt blog feed
git commit -m "$1"
git push

echo "done: portfolio rebuilt and pushed"
