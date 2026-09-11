# Card Copy Principles (the OK state)

Distilled 2026-09-10 from the swar-popcount-64 pilot review. Every card on the
portfolio and every future card, demo, and blog post must meet these at a
minimum. AAA standard: the reader never has to ask "what does that mean".

## 0. WHY is the primary requirement

- Every card answers WHY, not just WHAT. Every card carries all five layer
  slots: ISA, MICROARCH, FIRMWARE, KERNEL, ALGORITHM.
- Every slot needs a one-sentence because. Every because needs a formal
  evidence-backed Wigmore argument in data/wigmore.json. A card without all
  five arguments is not shippable.
- Dim slots require honest negative arguments and evidence too.
- THE VERDICT FOLLOWS THE ARGUMENT, NEVER THE REVERSE. A slot is lit or
  dimmed because the Wigmore analysis proves it so, from the taxonomy
  definitions and the card's evidence. Pre-existing lit/dim assignments are
  never accepted on faith: every verdict is re-derived from first principles.
  If the argument contradicts the old verdict, the verdict changes.
  Decision tests: ISA lights iff the verified claim depends on the machine
  contract (instructions, CSRs, traps, memory model). MICROARCH lights iff
  the card measures or reasons about implementation behavior (pipelines,
  caches, predictors, timing, contention). FIRMWARE lights iff the card
  depends on boot-time machine-mode config (PMP, trap delegation, SBI, misa
  dispatch); merely running under QEMU does not light it. KERNEL lights iff
  the card implements or depends on a kernel subsystem and the verification
  involved it. ALGORITHM lights iff the core verified claim is a pure
  computational mechanism portable across ISAs. Mere mention of a layer's
  vocabulary never lights it.

## 1. One surface, one job

- The summary is the MECHANISM only: what it does, how it works, why the
  argument travels. Three short sentences max.
- Stats live in the facts table. The receipt lives in the VERIFICATION row.
- No number appears twice. If a figure is in the facts, it is not in the
  summary.

## 2. Plain language first, jargon in parentheses

- Never the reverse. "10,000,133 inputs checked against the compiler's
  built-in popcount (`__builtin_popcountll`), 0 mismatches."
- The technical name stays for precision, but the sentence leads with what
  actually happened.

## 3. State the outcome with the method

- "DIFF TEST: 10,000,133 comparisons" is method without payoff. Merge the
  result into the same row: what was done AND what it proved.

## 4. No pronouns across rows

- Every row reads as a complete thought on its own. "WHERE NEEDED" and
  "USE THIS INSTEAD ON" force cross-row pronoun resolution. Name the thing:
  "WITHOUT cpop".

## 5. The verification row is a doorway, not a restatement

- It describes what's behind the link: "Full evidence: build log, raw test
  output, what the numbers mean." It never repeats CORRECTNESS's numbers.

## 6. Never claim testing that didn't happen

- "Checked against the hardware instruction" implies silicon testing. If the
  proof was host-only against a compiler builtin, say what the code IS
  ("Portable C implementation of the cpop operation") and let the evidence
  rows carry the proof.

## 7. Contrast needs data; an empty row is worse than no row

- A WITH/WITHOUT row renders only when the registry supports it. Every chip
  claim needs a vendor citation (datasheet section + URL).

## 8. Connect synonymous terms at first contact

- population count / popcount / cpop / POPCNT are one operation in four
  costumes. The HARDWARE row names what the instruction does in plain words
  the first time the reader meets it.

## 9. The instruction is the spec; the chip list is the deployment reality

- Frame portability as "same answers, different price": the instruction is
  the standard, the C is the substitute, the COST row is what equivalence
  costs without the silicon.

## 10. Label case is consistent

- All facts-table labels are ALL CAPS. No mixed-case strays.

## Banned in card copy

- Spec labels: DIFF TEST, TIMED LOAD, RESULT, WHERE NEEDED (all replaced).
- "differential-tested" / "differential test" as unexplained jargon.
- Comma-formatted thousands (10,000,133), throughput units (ns/value,
  Mvalues/s), "mismatches", "checksum", "comparisons" inside summaries.
- Hardware-test implications without hardware tests.

## Blog posts (judgment)

Blog posts follow the Blog First Principles (AGENTS.md). Applied here:
- Excerpts are mechanism + the one atomic idea, never stat dumps.
- The same plain-language-first rule for any term the post depends on.
- Numbers get human-scale intuition on first appearance (existing rule).
