#!/usr/bin/env python3
"""Drift gate for the portfolio Phase 2b static-build cutover (Worker 2).

Verifies every portfolio card's numeric claims against the machine-readable
<!-- PROOF-HEADER --> blocks stamped in the source repos during Phase 2a.

Usage:
    python3 drift-gate.py --cards <cards.json> --systems-lab <dir> \
        --baremetal <dir> --xv6 <dir>

Output: one line per card, sorted by card id:
    PASS <id>
    SKIP <id> <reason>
    FAIL <id> <field> card=<value> header=<value>
then a summary line:
    GATE: <p> pass, <s> skip, <f> fail

Exit code is 0 iff there are zero FAIL lines. A FAIL means a genuine
contradiction between the card and the stamped header. Missing data on
either side is a SKIP, never a FAIL. This script is read-only: it never
modifies repos, checkouts, or card data.
"""

import argparse
import json
import os
import re
import sys

HEADER_RE = re.compile(r'<!--\s*PROOF-HEADER(.*?)-->', re.S)
HEX_RE = re.compile(r'0x[0-9a-fA-F]+')
FLOAT_RE = re.compile(r'[-+]?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][-+]?\d+)?')
TAG_RE = re.compile(r'<[^>]*>')
THROUGHPUT_LABEL_RE = re.compile(r'measured|throughput|speed|ns/value', re.I)
CHECKSUM_LABEL_RE = re.compile(r'checksum', re.I)
TREE_PATH_RE = re.compile(r'/tree/main/([^?#]*)')

# Card id -> (repo key, repo-relative PROOF.md path). Checked in
# resolve_proof before the terminalName derivation. Repo keys are
# 'baremetal' (riscv-baremetal-demo) and 'systems-lab'.
CARD_MODULE_OVERRIDES = {
    'riscv-preemptive-scheduler': ('baremetal', 'src/preempt/PROOF.md'),
    'scheduler-benchmarks-o0-o2': ('baremetal', 'src/preempt/PROOF.md'),
    'bare-metal-uart-shell': ('baremetal', 'src/shell/PROOF.md'),
    'riscv-smp-bring-up': ('baremetal', 'src/smp/PROOF.md'),
    'virtio-block-driver': ('baremetal', 'src/virtio-blk/PROOF.md'),
    'wait-free-ring-buffer': ('systems-lab', 'lab/01-spsc-ring-buffer/PROOF.md'),
    'treiber-stack': ('systems-lab', 'lab/07-lockfree-stack/PROOF.md'),
    'fuzz-harness': ('systems-lab', 'lab/05-fuzz-harness/PROOF.md'),
    'seqlock': ('systems-lab', 'lab/08-seqlock/PROOF.md'),
}


def parse_header_block(inner):
    """Parse the key: value lines inside one PROOF-HEADER block."""
    fields = {}
    for line in inner.splitlines():
        line = line.strip()
        if not line or line.startswith('<!--'):
            continue
        if ':' not in line:
            continue
        key, value = line.split(':', 1)
        fields[key.strip()] = value.strip()
    return fields


def find_headers(text):
    """All PROOF-HEADER blocks in a file, in document order."""
    return [parse_header_block(m.group(1)) for m in HEADER_RE.finditer(text)]


def read_text(path):
    with open(path, encoding='utf-8', errors='replace') as f:
        return f.read()


def terminal_segments(term):
    return [s for s in (p.strip() for p in str(term).split('/')) if s]


def ensure_proof_path(rel):
    rel = rel.strip().rstrip('/')
    if rel.lower().endswith('proof.md'):
        return rel
    return (rel + '/' if rel else '') + 'PROOF.md'


def resolve_proof(card, systems_lab, baremetal, xv6):
    """Map a card to its PROOF source.

    Returns ('file', (full_path, rel_path)), ('xv6', card_id), or
    ('skip', reason). The terminalName rule from the cutover plan is the
    primary mapping; the repoUrl /tree/main/<path> is a fallback when the
    terminalName-derived path has no file.
    """
    repo = card.get('repoUrl') or ''
    term = card.get('terminalName') or ''
    if 'xv6-getscount' in repo:
        return ('xv6', card.get('id'))
    override = CARD_MODULE_OVERRIDES.get(card.get('id'))
    if override:
        base_key, relpath = override
        base = baremetal if base_key == 'baremetal' else systems_lab
        full = os.path.join(base, relpath)
        if os.path.isfile(full):
            return ('file', (full, relpath))
        return ('skip', 'no PROOF.md at ' + relpath)
    if 'systems-lab' in repo:
        base = systems_lab
        is_baremetal = False
    elif 'riscv-baremetal-demo' in repo:
        base = baremetal
        is_baremetal = True
    else:
        return ('skip', 'unknown repo ' + repo)
    segs = terminal_segments(term)
    has_lab_or_src = any(s in ('lab', 'src') for s in segs)
    candidates = []
    if is_baremetal and not has_lab_or_src:
        # Root-mapped card (e.g. qemu / riscv64 / demo.elf).
        candidates.append(('PROOF.md', 'no root PROOF.md'))
    else:
        rel = ensure_proof_path('/'.join(segs[1:]))
        candidates.append((rel, 'no PROOF.md at ' + rel))
    m = TREE_PATH_RE.search(repo)
    if m:
        tree_rel = ensure_proof_path(m.group(1))
        if all(tree_rel != c[0] for c in candidates):
            candidates.append((tree_rel, 'no PROOF.md at ' + tree_rel))
    for relpath, _reason in candidates:
        full = os.path.join(base, relpath)
        if os.path.isfile(full):
            return ('file', (full, relpath))
    return ('skip', candidates[0][1])


def xv6_resolve_header(card_id, xv6dir):
    """Section-scoped header lookup for the two xv6 cards."""
    path = os.path.join(xv6dir, 'PROOF.md')
    if not os.path.isfile(path):
        return None, 'no PROOF.md at ' + path
    text = read_text(path)
    if card_id == 'xv6-syscall-accounting':
        m = re.search(r'(?ms)^##\s+getscount run log.*?(?=^##\s+|\Z)', text)
        scope = m.group(0) if m else ''
        headers = find_headers(scope)
        if not headers:
            return None, 'no PROOF-HEADER in getscount run log section'
        return headers[0], None
    if card_id == 'xv6-nprocs-syscall':
        m = re.search(r'(?ms)^##\s+getscount run log', text)
        scope = text[:m.start()] if m else text
        headers = find_headers(scope)
        if not headers:
            return None, 'no PROOF-HEADER in nprocs section'
        return headers[0], None
    return None, 'unknown xv6 card ' + str(card_id)


def to_int(value):
    if value is None:
        return None
    s = str(value).strip().replace(',', '').replace(' ', '')
    if re.fullmatch(r'[-+]?\d+', s):
        try:
            return int(s)
        except ValueError:
            return None
    return None


def first_float(value):
    m = FLOAT_RE.search(str(value))
    return float(m.group()) if m else None


OPT_FLAG_RE = re.compile(r'-O(?:[0-3sz]|fast)(?![\w])')
TERMINAL_UNIT_RE = re.compile(r'ns/value|MiB/s|Mops/s|M values/s', re.I)


def floats_of(value):
    """All floats in a string. Compiler -O flags are stripped first so
    '-O2' does not contribute a spurious 2.0 that would fake a match."""
    text = OPT_FLAG_RE.sub('', str(value))
    return [float(m.group()) for m in FLOAT_RE.finditer(text)]


def rates_match(a, b):
    """2% relative tolerance; exact match required if either is 0."""
    if a == 0 or b == 0:
        return a == b
    return abs(a - b) / max(abs(a), abs(b)) <= 0.02


def norm_hex(token):
    t = token.strip().lower()
    if t.startswith('0x'):
        t = t[2:]
    return t


def card_checksum_tokens(card):
    """0x-prefixed hex tokens from checksum-labeled spec rows and from
    terminal output lines that mention 'checksum'. Other hex (addresses
    etc.) is ignored."""
    toks = []
    for row in card.get('specRows') or []:
        label = str(row[0]) if len(row) > 0 else ''
        value = str(row[1]) if len(row) > 1 else ''
        if CHECKSUM_LABEL_RE.search(label):
            toks.extend(HEX_RE.findall(value))
    text = TAG_RE.sub('', str(card.get('terminalOutput') or ''))
    for line in text.splitlines():
        if 'checksum' in line.lower():
            toks.extend(HEX_RE.findall(line))
    return toks


def evaluate(card, header):
    """Run the per-card checks. Returns (status, detail).

    status PASS: every applicable check agreed. FAIL: a contradiction was
    found; detail is (field, card_value, header_value). SKIP: no check had
    data on both sides; detail is the reason.
    """
    failures = []
    ran = 0

    card_checks = to_int(card.get('checks'))
    header_checks = to_int(header.get('Checks'))
    if card_checks is not None and header_checks is not None:
        ran += 1
        if card_checks != header_checks:
            failures.append(('checks', card_checks, header_checks))

    card_failures = to_int(card.get('failures'))
    header_mismatches = to_int(header.get('Mismatches'))
    if card_failures is not None and header_mismatches is not None:
        ran += 1
        if card_failures != header_mismatches:
            failures.append(('failures', card_failures, header_mismatches))

    tokens = card_checksum_tokens(card)
    header_checksum = header.get('Checksum')
    if tokens and header_checksum:
        ran += 1
        expected = norm_hex(header_checksum)
        for token in tokens:
            if norm_hex(token) != expected:
                failures.append(('checksum', token, header_checksum))
                break

    card_rates = []
    for row in card.get('specRows') or []:
        label = str(row[0]) if len(row) > 0 else ''
        if THROUGHPUT_LABEL_RE.search(label):
            card_rates.extend(
                floats_of(str(row[1]) if len(row) > 1 else ''))
    text = TAG_RE.sub('', str(card.get('terminalOutput') or ''))
    for line in text.splitlines():
        if TERMINAL_UNIT_RE.search(line):
            card_rates.extend(floats_of(line))
    header_rates = floats_of(header.get('Throughput') or '')
    if card_rates and header_rates:
        ran += 1
        if not any(rates_match(h, c)
                   for h in header_rates for c in card_rates):
            failures.append(('throughput', card_rates[0], header_rates[0]))

    card_env = (card.get('verificationEnvironment') or '').strip()
    header_env = (header.get('Environment') or '').strip()
    if card_env and header_env:
        ran += 1
        cl, hl = card_env.lower(), header_env.lower()
        if not (cl == hl or cl.startswith(hl) or hl.startswith(cl)):
            failures.append(('environment', card_env, header_env))

    if failures:
        return ('FAIL', failures[0])
    if ran == 0:
        return ('SKIP', 'no comparable data')
    return ('PASS', None)


def main(argv=None):
    ap = argparse.ArgumentParser(
        description='Verify portfolio card claims against PROOF-HEADER blocks.')
    ap.add_argument('--cards', required=True,
                    help='JSON file holding an array of card objects')
    ap.add_argument('--systems-lab', required=True,
                    help='systems-lab checkout directory')
    ap.add_argument('--baremetal', required=True,
                    help='riscv-baremetal-demo checkout directory')
    ap.add_argument('--xv6', required=True,
                    help='xv6-getscount checkout directory')
    args = ap.parse_args(argv)

    with open(args.cards, encoding='utf-8') as f:
        cards = json.load(f)

    lines = []
    n_pass = n_skip = n_fail = 0
    for card in sorted(cards, key=lambda c: str(c.get('id', ''))):
        cid = card.get('id', '?')
        kind, payload = resolve_proof(
            card, args.systems_lab, args.baremetal, args.xv6)
        if kind == 'skip':
            lines.append('SKIP %s %s' % (cid, payload))
            n_skip += 1
            continue
        if kind == 'xv6':
            header, err = xv6_resolve_header(payload, args.xv6)
            if err:
                lines.append('SKIP %s %s' % (cid, err))
                n_skip += 1
                continue
        else:
            full, relpath = payload
            headers = find_headers(read_text(full))
            if not headers:
                lines.append('SKIP %s no PROOF-HEADER in %s' % (cid, relpath))
                n_skip += 1
                continue
            header = headers[0]
        status, detail = evaluate(card, header)
        if status == 'PASS':
            lines.append('PASS %s' % cid)
            n_pass += 1
        elif status == 'SKIP':
            lines.append('SKIP %s %s' % (cid, detail))
            n_skip += 1
        else:
            field, card_value, header_value = detail
            lines.append('FAIL %s %s card=%s header=%s'
                         % (cid, field, card_value, header_value))
            n_fail += 1

    for line in lines:
        print(line)
    print('GATE: %d pass, %d skip, %d fail' % (n_pass, n_skip, n_fail))
    return 0 if n_fail == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
