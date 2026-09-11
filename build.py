#!/usr/bin/env python3
"""Build the portfolio index.html from canonical data files.

Flow:
  1. Load and validate data/cards.json, data/articles.json, data/chips.json,
     data/isa-decisions.json, data/wigmore.json.
  2. Run drift-gate.py against the source PROOF.md checkouts. Abort on any
     real contradiction (gate exit != 0). index.html is never touched then.
  3. Bake the data into index.src.html at build time:
       - /*__PROJECTS_JSON__*/ -> the 140 cards (deterministic JSON)
       - /*__CHIPS_JSON__*/    -> chips keyed by chip key (deterministic JSON)
       - /*__WIGMORE_JSON__*/  -> Wigmore slot analyses, keyed "item|slot"
       - <!-- LAYER-STRIP:<slug> --> (x10) -> static article layer strips
  4. node --check every generated <script> block.
  5. Write index.html only if everything above succeeded.

The delivered page stays fully static: no runtime fetching, no dynamic
data loading. Edit data/*.json, then run build-portfolio.sh "message".
"""

import argparse
import datetime
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

LAYERS = ("ISA", "MICROARCH", "FIRMWARE", "KERNEL", "ALGORITHM")
# Layers every item must carry a verdict for. MICROARCH joins this set once
# the pilot extension is approved; until then it is optional and its absence
# only warns (warn() never fails the build, fail() does).
LAYERS_REQUIRED = ("ISA", "FIRMWARE", "KERNEL", "ALGORITHM")
PORTABILITY_FIELDS = ("instruction", "extension", "specRef", "specUrl", "whereNeeded", "costNote")
PORTABILITY_OPTIONAL_FIELDS = ("instructionWhat",)
WIGMORE_KINDS = ("probandum", "penultimate", "evidence", "generalization",
                 "explanation", "refutation")
WIGMORE_TIERS = ("lab", "spec", "vendor", "reference", "community")
WIGMORE_STRENGTHS = ("strong", "normal", "weak")


class BuildError(Exception):
    pass


# Items still missing a MICROARCH verdict during the pilot phase. Summarized
# once after validation instead of warning per item.
_pilot_missing_microarch = []


def fail(msg):
    raise BuildError(msg)


def warn(msg):
    # Warnings never fail the build; they are the second pair of eyes for
    # the partial-correctness error mode (a layer that should be lit but
    # is dim or missing). A human reads them before shipping.
    print(f"WARNING: {msg}")


# Keyword lint against the partial-correctness error mode: when an item's
# prose leans on a layer's subject matter while that slot is dim or absent,
# flag it for human review. Warning only; the checklist in the slot
# authoring pass is the primary defense, this is the backstop.
LAYER_TRIGGERS = {
    "MICROARCH": (r"cache", r"pipeline", r"hazard", r"prefetch",
                  r"branch predict", r"superscalar", r"out-of-order",
                  r"store buffer"),
    "FIRMWARE": (r"\bSBI\b", r"\bPMP\b", r"\bmisa\b", r"M-mode",
                 r"machine mode", r"bootloader", r"boot ROM"),
    "KERNEL": (r"syscall", r"schedul", r"page table", r"virtual memory",
               r"context switch", r"\bdriver\b"),
    "ISA": (r"instruction", r"\bCSR\b", r"opcode", r"illegal instruction",
            r"extension", r"memory model", r"\bfence\b"),
}


def lint_layer_triggers(text, layers, where):
    import re
    for layer, patterns in LAYER_TRIGGERS.items():
        slot = layers.get(layer)
        if slot and slot.get("applies"):
            continue
        for pat in patterns:
            if re.search(pat, text, re.IGNORECASE):
                state = "dim" if slot else "missing"
                warn(f"{where}: prose mentions {pat!r} but {layer} is {state}; "
                     f"check for under-highlighting")
                break


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
    if not isinstance(layers, dict):
        fail(f"{where}: layers must be a dict")
    keys = set(layers.keys())
    if not set(LAYERS_REQUIRED) <= keys <= set(LAYERS):
        fail(f"{where}: layers must include {LAYERS_REQUIRED} and only {LAYERS}")
    if "MICROARCH" not in keys:
        _pilot_missing_microarch.append(where)
    for name in keys:
        slot = layers[name]
        if not isinstance(slot, dict) or set(slot.keys()) != {"applies", "because"}:
            fail(f"{where}: layer {name} must be {{applies, because}}")
        if not isinstance(slot["applies"], bool):
            fail(f"{where}: layer {name} applies must be boolean")
        b = slot["because"]
        if not isinstance(b, str) or not b.strip():
            fail(f"{where}: layer {name} because must be a non-empty string")
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
    if not isinstance(p, dict) or not set(PORTABILITY_FIELDS) <= set(p.keys()) <= set(PORTABILITY_FIELDS + PORTABILITY_OPTIONAL_FIELDS):
        fail(f"{where}: portability must have exactly {PORTABILITY_FIELDS} plus optionally {PORTABILITY_OPTIONAL_FIELDS}")
    for f in ("instruction", "extension", "specRef", "costNote"):
        if not isinstance(p[f], str) or not p[f].strip():
            fail(f"{where}: portability.{f} must be a non-empty string")
    if "instructionWhat" in p and (not isinstance(p["instructionWhat"], str) or not p["instructionWhat"].strip()):
        fail(f"{where}: portability.instructionWhat must be a non-empty string")
    if not isinstance(p["whereNeeded"], list) or not p["whereNeeded"]:
        fail(f"{where}: portability.whereNeeded must be a non-empty list")
    for key in p["whereNeeded"]:
        if key not in chip_keys:
            fail(f"{where}: portability.whereNeeded references unknown chip {key!r}")
    u = p["specUrl"]
    if not u.startswith("https://"):
        fail(f"{where}: portability.specUrl must be an https URL")
    if any(ch in u for ch in " '\"<>"):
        fail(f"{where}: portability.specUrl contains unsafe characters")


def check_decisions(decisions, card_ids):
    # The structured argument store for ISA-mapping decisions: every accepted
    # hardware treatment and every deliberately rejected near-mapping, each
    # with its rationale and external primary sources. Claim discipline from
    # Chris 2026-09-10: argument data kept structured, evidence linked.
    if not isinstance(decisions, list) or not decisions:
        fail("isa-decisions.json must be a non-empty list")
    seen = set()
    for d in decisions:
        for f in ("id", "cardId", "decision", "claim", "rationale", "sources"):
            if f not in d:
                fail(f"decision missing field {f}: {d.get('id')}")
        if d["id"] in seen:
            fail(f"duplicate decision id {d['id']}")
        seen.add(d["id"])
        if d["decision"] not in ("accepted", "rejected"):
            fail(f"decision {d['id']}: must be accepted or rejected")
        if d["cardId"] not in card_ids:
            fail(f"decision {d['id']}: unknown card {d['cardId']}")
        if d["decision"] == "accepted" and not d.get("instruction"):
            fail(f"decision {d['id']}: accepted needs an instruction")
        if not isinstance(d["sources"], list) or not d["sources"]:
            fail(f"decision {d['id']}: needs at least one source")
        for s in d["sources"]:
            if set(s.keys()) != {"kind", "label", "url"}:
                fail(f"decision {d['id']}: source must be {{kind, label, url}}")
            if s["kind"] not in ("spec", "vendor-doc", "paper", "proof-log"):
                fail(f"decision {d['id']}: unknown source kind {s['kind']}")
            if not s["url"].startswith("https://"):
                fail(f"decision {d['id']}: source url must be https")


def check_wigmore(doc, card_ids, article_slugs):
    # Formal Wigmore argument store: one analysis per card/article per layer
    # slot. Pilot phase (2026-09-10): partial coverage is allowed; every
    # analysis present is validated strictly. After Chris approves the pilot,
    # coverage becomes mandatory for all 608 slots.
    if not isinstance(doc, dict) or doc.get("version") != 1:
        fail("wigmore.json must be {version: 1, analyses: [...]}")
    analyses = doc.get("analyses")
    if not isinstance(analyses, list) or not analyses:
        fail("wigmore.json analyses must be a non-empty list")
    seen = set()
    for a in analyses:
        for f in ("item", "kind", "slot", "probandum", "keyList", "inferences"):
            if f not in a:
                fail(f"wigmore analysis missing field {f}: {a.get('item')}/{a.get('slot')}")
        key = (a["item"], a["slot"])
        if key in seen:
            fail(f"duplicate wigmore analysis {key}")
        seen.add(key)
        if a["kind"] == "card":
            if a["item"] not in card_ids:
                fail(f"wigmore analysis {key}: unknown card")
        elif a["kind"] == "article":
            if a["item"] not in article_slugs:
                fail(f"wigmore analysis {key}: unknown article slug")
        else:
            fail(f"wigmore analysis {key}: kind must be card or article")
        if a["slot"] not in LAYERS:
            fail(f"wigmore analysis {key}: unknown slot")
        nodes = {}
        for e in a["keyList"]:
            for f in ("n", "kind", "text"):
                if f not in e:
                    fail(f"wigmore {key}: keyList entry missing {f}")
            if e["n"] in nodes:
                fail(f"wigmore {key}: duplicate node n={e['n']}")
            nodes[e["n"]] = e
            if e["kind"] not in WIGMORE_KINDS:
                fail(f"wigmore {key}: unknown node kind {e['kind']}")
            if not isinstance(e["text"], str) or not e["text"].strip():
                fail(f"wigmore {key}: node {e['n']} text must be non-empty")
            if any(ch in e["text"] for ch in "<>&"):
                fail(f"wigmore {key}: node {e['n']} text contains <, > or &")
            if "—" in e["text"]:
                fail(f"wigmore {key}: node {e['n']} text contains an em dash")
            if e["kind"] == "evidence":
                s = e.get("source")
                if (not isinstance(s, dict) or s.get("tier") not in WIGMORE_TIERS
                        or not isinstance(s.get("url"), str)
                        or not s["url"].startswith("https://")
                        or any(ch in s["url"] for ch in " '\"<>")):
                    fail(f"wigmore {key}: evidence node {e['n']} needs "
                         f"{{tier in {WIGMORE_TIERS}, url: safe https URL}}")
        if sum(1 for e in nodes.values() if e["kind"] == "probandum") != 1:
            fail(f"wigmore {key}: exactly one probandum required")
        probandum = next(n for n, e in nodes.items() if e["kind"] == "probandum")
        for inf in a["inferences"]:
            for f in ("from", "via", "to", "strength"):
                if f not in inf:
                    fail(f"wigmore {key}: inference missing {f}")
            if inf["strength"] not in WIGMORE_STRENGTHS:
                fail(f"wigmore {key}: unknown strength {inf['strength']}")
            for n in inf["from"]:
                if nodes[n]["kind"] not in ("evidence", "penultimate"):
                    fail(f"wigmore {key}: inference from-node {n} must be "
                         f"evidence or penultimate")
            for n in inf["via"]:
                if nodes[n]["kind"] != "generalization":
                    fail(f"wigmore {key}: inference via-node {n} must be a "
                         f"generalization")
            for n in inf["to"]:
                if nodes[n]["kind"] not in ("probandum", "penultimate"):
                    fail(f"wigmore {key}: inference to-node {n} must be "
                         f"probandum or penultimate")
        # Reachability: the probandum must be reachable from evidence through
        # the inference graph, otherwise the argument proves nothing.
        evidence = {n for n, e in nodes.items() if e["kind"] == "evidence"}
        reach = set(evidence)
        changed = True
        while changed:
            changed = False
            for inf in a["inferences"]:
                if all(x in reach for x in inf["from"]):
                    for t in inf["to"]:
                        if t not in reach:
                            reach.add(t)
                            changed = True
        if probandum not in reach:
            fail(f"wigmore {key}: probandum not reachable from evidence")
    return {(a["item"], a["slot"]): a for a in analyses}


def load_data():
    try:
        cards = json.loads((DATA / "cards.json").read_text(encoding="utf-8"))
        articles = json.loads((DATA / "articles.json").read_text(encoding="utf-8"))
        chips = json.loads((DATA / "chips.json").read_text(encoding="utf-8"))
        decisions = json.loads((DATA / "isa-decisions.json").read_text(encoding="utf-8"))
        wigmore = json.loads((DATA / "wigmore.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        fail(f"could not parse data files: {e}")

    if not isinstance(cards, list) or len(cards) < 140:
        fail(f"cards.json must hold at least 140 cards, found {len(cards) if isinstance(cards, list) else type(cards)}")
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
        lint_layer_triggers(
            " ".join(str(c.get(f, "")) for f in ("title", "summary", "kicker")),
            c["layers"], f"card {c['id']}")

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

    check_decisions(decisions, set(seen))
    # The argument store and the panels must agree: every accepted decision
    # has a portability block and vice versa.
    accepted = {d["cardId"] for d in decisions if d["decision"] == "accepted"}
    panelled = {c["id"] for c in cards if c.get("portability")}
    if accepted != panelled:
        fail(f"isa-decisions accepted {sorted(accepted ^ panelled)} != portability cards")

    if not isinstance(articles, list) or len(articles) < 10:
        fail(f"articles.json must hold at least 10 articles, found {len(articles) if isinstance(articles, list) else type(articles)}")
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
        lint_layer_triggers(
            a["title"] + " " + " ".join(a["paragraphs"]),
            a["layers"], f"article {a['title']}")

    article_slugs = {slugify(a["title"]) for a in articles}
    wigmore_by_slot = check_wigmore(wigmore, set(seen), article_slugs)
    print(f"wigmore: {len(wigmore_by_slot)} slot analyses validated")
    if _pilot_missing_microarch:
        print(f"pilot: {len(_pilot_missing_microarch)} items without a MICROARCH "
              f"verdict (expected until the pilot extension is approved)")

    return cards, articles, chips_by_key, decisions, wigmore_by_slot


def run_copy_gate(cards, articles):
    # Card copy OK-state gate (CARD_COPY_PRINCIPLES.md): banned spec labels,
    # no stat-dumping in summaries/excerpts, instructionWhat required on
    # portability blocks. A run whose cards fail this ships no site change.
    banned_labels = {"DIFF TEST", "TIMED LOAD", "RESULT", "WHERE NEEDED",
                       "CHECKS", "MISMATCHES", "VERDICT", "THROUGHPUT",
                       "MEASURED", "SPEED"}
    stat_patterns = [
        re.compile(r"\d{1,3}(,\d{3})+"),  # comma-formatted thousands
        re.compile(r"ns/value", re.I),
        re.compile(r"Mvalues", re.I),
        # counted test outcomes ("0 mismatches", "2088 comparisons"): a bare
        # "comparison" is ordinary mechanism vocabulary, so require a count
        re.compile(r"\b(?:\d[\d,]*|zero|no)\s+mismatches?\b", re.I),
        re.compile(r"\b\d[\d,]*\s+comparisons?\b", re.I),
        re.compile(r"\bchecksums?\b", re.I),
    ]
    errors = []
    for c in cards:
        cid = c.get("id", "?")
        for row in c.get("specRows") or []:
            if row[0] in banned_labels:
                errors.append(f"{cid}: banned spec label {row[0]!r}")
            elif row[0] != row[0].upper():
                errors.append(f"{cid}: spec label not ALL CAPS: {row[0]!r}")
        summary = c.get("summary", "")
        if any(p.search(summary) for p in stat_patterns):
            errors.append(f"{cid}: summary dumps stats")
        p = c.get("portability")
        if p and not p.get("instructionWhat"):
            errors.append(f"{cid}: portability missing instructionWhat")
    for a in articles:
        excerpt = a.get("excerpt", "") or a.get("summary", "")
        if any(p.search(excerpt) for p in stat_patterns):
            errors.append(f"article {a.get('id', '?')}: excerpt dumps stats")
    if errors:
        fail("copy gate: card copy below OK state:\n  " + "\n  ".join(errors))
    print(f"copy gate: OK ({len(cards)} cards, {len(articles)} articles)")


def run_why_quality_gate(cards, decisions, wigmore_by_slot):
    # WHY reasoning standard (from Chris 2026-09-11): every layer because
    # must be a card-specific argument, never a checklist. The setup is never
    # the argument. These frames are the known checklist patterns; a run
    # whose becauses match them ships no site change.
    checklist = [
        re.compile(r"ran on (a|the) host\b", re.I),
        re.compile(r"host machine\b", re.I),
        re.compile(r"\bhost CPU\b", re.I),
        re.compile(r"compared outputs on a host\b", re.I),
        re.compile(r"runs? in user space with no\b", re.I),
        re.compile(r"\bno (kernel|firmware) subsystem is involved\b", re.I),
        re.compile(r"not a (kernel|firmware|microarch[a-z]*) subsystem\b", re.I),
        re.compile(r"no (?:[\w\-/]+ )+instruction ever executed\b", re.I),
        re.compile(r"recorded no (pipeline|cache|predictor)", re.I),
        re.compile(r"alone cannot light\b", re.I),
        re.compile(r"exercised no\b", re.I),
        re.compile(r"touches? nothing\b", re.I),
        re.compile(r"appears? nowhere\b", re.I),
    ]
    errors = []
    for c in cards:
        cid = c.get("id", "?")
        for layer in LAYERS:
            slot = (c.get("layers") or {}).get(layer) or {}
            because = slot.get("because", "")
            for pat in checklist:
                if pat.search(because):
                    errors.append(f"{cid}/{layer}: checklist phrasing "
                                  f"{pat.pattern!r}")
                    break
            key = (cid, layer)
            analysis = wigmore_by_slot.get(key)
            if analysis is None:
                errors.append(f"{cid}/{layer}: no wigmore analysis")
            elif analysis.get("probandum") != because:
                errors.append(f"{cid}/{layer}: because != analysis probandum")
    # isa-decisions.json is authoritative for specification correspondence:
    # every accepted instruction mapping must have its card's ISA slot lit.
    accepted = {d["cardId"] for d in decisions if d["decision"] == "accepted"}
    for c in cards:
        cid = c.get("id", "?")
        if cid in accepted:
            slot = (c.get("layers") or {}).get("ISA") or {}
            if not slot.get("applies"):
                errors.append(f"{cid}: isa-decisions accepts an instruction "
                              f"mapping but the ISA slot is dim")
    if errors:
        fail("why gate: layer arguments below standard:\n  " + "\n  ".join(errors))
    print(f"why gate: OK ({len(cards)} cards, "
          f"{len(wigmore_by_slot)} slot arguments)")


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
    # One proof-log link per article, on the strip caption; per-slot evidence
    # links were removed as redundant.
    ev = article.get("evidence") or {}
    proof_html = ""
    if ev:
        proof_html = (
            f'<a class="card-proof" href="{html.escape(ev["url"], quote=True)}"'
            f' target="_blank" rel="noopener">'
            f'{html.escape(ev["label"], quote=False)}'
            f' <span aria-hidden="true">\u2197</span></a>'
        )
    slots = []
    for name in LAYERS:
        if name not in article["layers"]:
            continue  # pilot: only the pilot card carries MICROARCH so far
        slot = article["layers"][name]
        cls = "layer-slot lit" if slot["applies"] else "layer-slot dim"
        because = html.escape(slot["because"], quote=False)
        slots.append(
            f'<div class="{cls}"><div class="layer-name">{name}</div>'
            f'<p class="layer-because">{because}</p></div>'
        )
    return ('<div class="layer-strip">'
            '<div class="layer-strip-caption"><span>Relevance by layer</span>'
            + proof_html + '</div>'
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
    cards, articles, chips_by_key, decisions, wigmore_by_slot = load_data()
    print(f"data OK: {len(cards)} cards, {len(articles)} articles, "
          f"{len(chips_by_key)} chips, "
          f"{sum(1 for c in cards if c.get('portability'))} portability panels")

    run_copy_gate(cards, articles)
    run_why_quality_gate(cards, decisions, wigmore_by_slot)
    run_gate(systems_lab, baremetal, xv6)
    print("drift gate: no contradictions")

    template = SRC.read_text(encoding="utf-8")

    projects_json = json.dumps(cards, indent=2, ensure_ascii=False)
    chips_json = json.dumps(chips_by_key, indent=2, ensure_ascii=False)
    # Keyed "item|slot" for O(1) lookup by the tooltip renderer.
    wigmore_json = json.dumps(
        {f"{item}|{slot}": a for (item, slot), a in wigmore_by_slot.items()},
        indent=2, ensure_ascii=False)

    if template.count("/*__PROJECTS_JSON__*/") != 1:
        fail("expected exactly one /*__PROJECTS_JSON__*/ placeholder")
    if template.count("/*__CHIPS_JSON__*/") != 1:
        fail("expected exactly one /*__CHIPS_JSON__*/ placeholder")
    if template.count("/*__WIGMORE_JSON__*/") != 1:
        fail("expected exactly one /*__WIGMORE_JSON__*/ placeholder")
    page = template.replace("/*__PROJECTS_JSON__*/", projects_json)
    page = page.replace("/*__CHIPS_JSON__*/", chips_json)
    page = page.replace("/*__WIGMORE_JSON__*/", wigmore_json)

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

    for leftover in ("__PROJECTS_JSON__", "__CHIPS_JSON__", "__WIGMORE_JSON__", "LAYER-STRIP:"):
        if leftover in page:
            fail(f"unresolved placeholder remains: {leftover}")

    # Stamp a unique build version so the foreground update check and the
    # service worker both notice every deploy. Without this, phones keep
    # serving the previous cached page forever.
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("v%Y%m%d-%H%M%S")
    page, n = re.subn(r'(<meta name="build-version" content=")[^"]*(">)', r"\g<1>" + stamp + r"\g<2>", page)
    if n != 1:
        fail("expected exactly one build-version meta tag")
    sw_path = HERE / "sw.js"
    sw_text = sw_path.read_text(encoding="utf-8")
    sw_text, m = re.subn(r"(const VERSION = ')[^']*(')", r"\g<1>" + stamp + r"\g<2>", sw_text)
    if m != 1:
        fail("expected exactly one VERSION in sw.js")
    sw_path.write_text(sw_text, encoding="utf-8")

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
