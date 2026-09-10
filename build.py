#!/usr/bin/env python3
"""Build the portfolio index.html from canonical data files.

Flow:
  1. Load and validate data/cards.json, data/articles.json, data/chips.json.
  2. Run drift-gate.py against the source PROOF.md checkouts. Abort on any
     real contradiction (gate exit != 0). index.html is never touched then.
  3. Bake the data into index.src.html at build time:
       - /*__PROJECTS_JSON__*/ -> the 140 cards (deterministic JSON)
       - /*__CHIPS_JSON__*/    -> chips keyed by chip key (deterministic JSON)
       - <!-- LAYER-STRIP:<slug> --> (x9) -> static article layer strips
  4. node --check every generated <script> block.
  5. Write index.html only if everything above succeeded.

The delivered page stays fully static: no runtime fetching, no dynamic
data loading. Edit data/*.json, then run build-portfolio.sh "message".
"""

import argparse
import html
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
SRC = HERE / "index.src.html"
OUT = HERE / "index.html"
GATE = HERE / "drift-gate.py"

LAYERS = ("ISA", "FIRMWARE", "KERNEL", "PORTABLE")
PORTABILITY_FIELDS = ("instruction", "extension", "specRef", "whereNeeded", "costNote")


class BuildError(Exception):
    pass


def fail(msg):
    raise BuildError(msg)


def check_evidence(ev, where):
    # Every layer strip's becauses must name primary evidence a reader can
    # follow: the card's PROOF.md proof log (or the repo itself when no
    # proof log exists). Claim discipline from Chris 2026-09-10.
    if not isinstance(ev, dict) or set(ev.keys()) != {"label", "url"}:
        fail(f"{where}: evidence must be {{label, url}}")
    if (not isinstance(ev["label"], str) or not ev["label"].strip()
            or any(ch in ev["label"] for ch in "<>&")):
        fail(f"{where}: evidence.label must be plain non-empty text")
    u = ev["url"]
    if (not isinstance(u, str)
            or not u.startswith("https://github.com/dillingerstaffing/")):
        fail(f"{where}: evidence.url must be an https://github.com/dillingerstaffing/ URL")
    if any(ch in u for ch in " '\"<>"):
        fail(f"{where}: evidence.url contains unsafe characters")


def check_layers(layers, where):
    if not isinstance(layers, dict) or set(layers.keys()) != set(LAYERS):
        fail(f"{where}: layers must have exactly {LAYERS}")
    for name in LAYERS:
        slot = layers[name]
        if not isinstance(slot, dict) or set(slot.keys()) != {"applies", "because"}:
            fail(f"{where}: layer {name} must be {{applies, because}}")
        if not isinstance(slot["applies"], bool):
            fail(f"{where}: layer {name} applies must be boolean")
        b = slot["because"]
        if not isinstance(b, str) or not b.strip():
            fail(f"{where}: layer {name} because must be a non-empty string")
        # because strings are plain text inserted into HTML: they must not
        # carry markup or entities, and Chris never uses em dashes.
        if any(ch in b for ch in "<>&"):
            fail(f"{where}: layer {name} because contains <, > or &: {b[:60]!r}")
        if "\u2014" in b:
            fail(f"{where}: layer {name} because contains an em dash")


def check_portability(p, where, chip_keys):
    if p is None:
        return
    if not isinstance(p, dict) or set(p.keys()) != set(PORTABILITY_FIELDS):
        fail(f"{where}: portability must have exactly {PORTABILITY_FIELDS}")
    for f in ("instruction", "extension", "specRef", "costNote"):
        if not isinstance(p[f], str) or not p[f].strip():
            fail(f"{where}: portability.{f} must be a non-empty string")
    if not isinstance(p["whereNeeded"], list) or not p["whereNeeded"]:
        fail(f"{where}: portability.whereNeeded must be a non-empty list")
    for key in p["whereNeeded"]:
        if key not in chip_keys:
            fail(f"{where}: portability.whereNeeded references unknown chip {key!r}")


def load_data():
    try:
        cards = json.loads((DATA / "cards.json").read_text(encoding="utf-8"))
        articles = json.loads((DATA / "articles.json").read_text(encoding="utf-8"))
        chips = json.loads((DATA / "chips.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        fail(f"could not parse data files: {e}")

    if not isinstance(cards, list) or len(cards) != 140:
        fail(f"cards.json must hold exactly 140 cards, found {len(cards) if isinstance(cards, list) else type(cards)}")
    seen = set()
    for c in cards:
        for f in ("id", "title", "summary", "specRows", "terminalOutput",
                  "verificationEnvironment", "checks", "failures", "layers"):
            if f not in c:
                fail(f"card missing field {f}: {c.get('id')}")
        if c["id"] in seen:
            fail(f"duplicate card id {c['id']}")
        seen.add(c["id"])
        if not isinstance(c["checks"], int) or not isinstance(c["failures"], int):
            fail(f"card {c['id']}: checks/failures must be ints")
        if not isinstance(c["specRows"], list) or not all(
                isinstance(r, list) and len(r) == 2 for r in c["specRows"]):
            fail(f"card {c['id']}: specRows must be [label, value] pairs")
        check_layers(c["layers"], f"card {c['id']}")
        check_evidence(c.get("evidence"), f"card {c['id']}")

    if not isinstance(chips, list) or not chips:
        fail("chips.json must be a non-empty list")
    chip_keys = set()
    chips_by_key = {}
    for chip in chips:
        for f in ("key", "name", "isaString", "source"):
            if f not in chip:
                fail(f"chip missing field {f}: {chip}")
        if chip["key"] in chip_keys:
            fail(f"duplicate chip key {chip['key']}")
        chip_keys.add(chip["key"])
        chips_by_key[chip["key"]] = chip

    for c in cards:
        check_portability(c.get("portability"), f"card {c['id']}", chip_keys)

    if not isinstance(articles, list) or len(articles) != 9:
        fail(f"articles.json must hold exactly 9 articles, found {len(articles) if isinstance(articles, list) else type(articles)}")
    seen_titles = set()
    for a in articles:
        for f in ("title", "date", "paragraphs", "codeLink", "layers"):
            if f not in a:
                fail(f"article missing field {f}: {a.get('title')}")
        if a["title"] in seen_titles:
            fail(f"duplicate article title {a['title']}")
        seen_titles.add(a["title"])
        if not isinstance(a["paragraphs"], list) or not a["paragraphs"]:
            fail(f"article {a['title']}: paragraphs must be a non-empty list")
        check_layers(a["layers"], f"article {a['title']}")
        check_evidence(a.get("evidence"), f"article {a['title']}")

    return cards, articles, chips_by_key


def run_gate(systems_lab, baremetal, xv6):
    cmd = [sys.executable, str(GATE),
           "--cards", str(DATA / "cards.json"),
           "--systems-lab", systems_lab,
           "--baremetal", baremetal,
           "--xv6", xv6]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    print(proc.stdout, end="")
    if proc.stderr:
        print(proc.stderr, file=sys.stderr, end="")
    if proc.returncode != 0:
        fail("drift gate reported contradictions; index.html was not modified")


def slugify(title):
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")


def article_strip_html(article):
    # Mirrors the layerStripHTML() renderer in index.src.html, but baked at
    # build time. because strings are validated plain text; escape anyway.
    ev = article.get("evidence") or {}
    ev_html = ""
    if ev:
        ev_html = (
            f'<a class="layer-source" href="{html.escape(ev["url"], quote=True)}"'
            f' target="_blank" rel="noopener">'
            f'{html.escape(ev["label"], quote=False)}'
            f' <span aria-hidden="true">\u2197</span></a>'
        )
    slots = []
    for name in LAYERS:
        slot = article["layers"][name]
        cls = "layer-slot lit" if slot["applies"] else "layer-slot dim"
        because = html.escape(slot["because"], quote=False)
        slots.append(
            f'<div class="{cls}"><div class="layer-name">{name}</div>'
            f'<p class="layer-because">{because}</p>{ev_html}</div>'
        )
    return ('<div class="layer-strip">'
            '<div class="layer-strip-caption">Relevance by layer</div>'
            + "".join(slots) + "</div>")


def node_check_scripts(html_text):
    # Only real JavaScript blocks: skip JSON-LD and any other typed data.
    scripts = []
    for m in re.finditer(r"<script([^>]*)>(.*?)</script>", html_text, re.S | re.I):
        attrs = m.group(1)
        if re.search(r'\btype\s*=\s*["\'](?!text/javascript|application/javascript|module)', attrs, re.I):
            continue
        scripts.append(m.group(2))
    if not scripts:
        fail("no inline <script> blocks found to check")
    for i, js in enumerate(scripts):
        with tempfile.NamedTemporaryFile("w", suffix=".js",
                                         delete=False, encoding="utf-8") as f:
            f.write(js)
            path = f.name
        proc = subprocess.run(["node", "--check", path],
                              capture_output=True, text=True)
        if proc.returncode != 0:
            fail(f"node --check failed on script block {i}: {proc.stderr.strip()}")
    print(f"node --check: {len(scripts)} script block(s) OK")


def build(systems_lab, baremetal, xv6):
    cards, articles, chips_by_key = load_data()
    print(f"data OK: {len(cards)} cards, {len(articles)} articles, "
          f"{len(chips_by_key)} chips, "
          f"{sum(1 for c in cards if c.get('portability'))} portability panels")

    run_gate(systems_lab, baremetal, xv6)
    print("drift gate: no contradictions")

    template = SRC.read_text(encoding="utf-8")

    projects_json = json.dumps(cards, indent=2, ensure_ascii=False)
    chips_json = json.dumps(chips_by_key, indent=2, ensure_ascii=False)

    if template.count("/*__PROJECTS_JSON__*/") != 1:
        fail("expected exactly one /*__PROJECTS_JSON__*/ placeholder")
    if template.count("/*__CHIPS_JSON__*/") != 1:
        fail("expected exactly one /*__CHIPS_JSON__*/ placeholder")
    page = template.replace("/*__PROJECTS_JSON__*/", projects_json)
    page = page.replace("/*__CHIPS_JSON__*/", chips_json)

    used_slugs = set()
    for article in articles:
        slug = slugify(article["title"])
        if slug in used_slugs:
            fail(f"duplicate article slug {slug}")
        used_slugs.add(slug)
        marker = f"<!-- LAYER-STRIP:{slug} -->"
        if page.count(marker) != 1:
            fail(f"expected exactly one {marker} placeholder")
        page = page.replace(marker, article_strip_html(article))

    for leftover in ("__PROJECTS_JSON__", "__CHIPS_JSON__", "LAYER-STRIP:"):
        if leftover in page:
            fail(f"unresolved placeholder remains: {leftover}")

    node_check_scripts(page)

    OUT.write_text(page, encoding="utf-8")
    print(f"wrote {OUT} ({len(page)} bytes)")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Build the portfolio index.html from data/*.json.")
    ap.add_argument("--systems-lab", default=str(Path.home() / "workspace/freelance-business/systems-lab"))
    ap.add_argument("--baremetal", default=str(Path.home() / "workspace/freelance-business/riscv-baremetal-demo"))
    ap.add_argument("--xv6", default=str(Path.home() / "workspace/freelance-business/xv6-getscount"))
    args = ap.parse_args(argv)
    try:
        build(args.systems_lab, args.baremetal, args.xv6)
    except BuildError as e:
        print(f"BUILD FAILED: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
