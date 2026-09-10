# Portfolio build

The portfolio page is a fully static site. All card, article, and chip
content lives as canonical data in `data/`:

- `data/cards.json` — the 140 proof cards (id, copy, spec rows, terminal
  output, checks, four-slot layer strip, optional portability mapping)
- `data/articles.json` — the 9 research articles (title, date, paragraphs,
  code link, four-slot layer strip)
- `data/chips.json` — the chip reference table (keyed by chip key at build
  time for the portability panels)

`index.src.html` is the page template. `index.html` is generated and is the
only file GitHub Pages serves. Never edit `index.html` by hand.

## Workflow

Edit the data, then build and deploy in one step:

```sh
./build-portfolio.sh "describe the change"
```

That runs `build.py`, which:

1. Parses and validates every data file (140 cards, 9 articles, chip keys;
   every layer strip has exactly four slots with a boolean `applies` and a
   plain-text one-sentence `because`; every non-null portability record has
   all five fields and references known chips).
2. Runs `drift-gate.py` against the `systems-lab`, `riscv-baremetal-demo`,
   and `xv6-getscount` checkouts. Any real contradiction between a card and
   its source PROOF.md aborts the build **without modifying `index.html`**.
3. Bakes the data into the template at build time: the card array and the
   chip table are inlined as JSON (no runtime fetching, no dynamic data
   loading), and each of the nine `<!-- LAYER-STRIP:<slug> -->` markers is
   replaced with static layer-strip HTML.
4. Runs `node --check` on every generated script block.
5. Writes `index.html` only if all of the above succeeded.

`build-portfolio.sh` then verifies the output (140 cards, 149 layer
strips, no unresolved placeholders), commits, and pushes.

## Rules

- Card numbers must match what the source PROOF.md asserts. If the gate
  fails, fix the card or the PROOF.md header, never weaken the gate.
- `because` strings are plain text: no `<`, `>`, `&`, no em dashes.
- Portability panels only where a verified ISA mapping exists; never
  stretch an algorithm card into a hardware claim.
