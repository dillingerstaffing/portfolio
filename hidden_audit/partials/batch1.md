# Batch 1 findings (worker completed 2026-09-21 02:20 EDT)

## who-writes-the-a-and-d-bits — 1 defect
- FIRMWARE: PARTIAL (applies=true). Only M-mode content is the phrase "bit 61 of the M-mode CSR menvcfg"; because describes M-mode setup (probing ADUE writability, PMP entry, medeleg delegation, ADUE flip on S-mode ecall) nowhere in the post. Either post must cover that setup or slot dims. Note: ISA because says ADUE is a "WARL field": true but not stated verbatim in the post (minor).
## its-a-trap — clean (5 OK). Minor: KERNEL because's "timer interrupt drives preemption" clause not in post (verdict still OK).
## the-comparison-that-leaves-no-trace — 1 defect
- KERNEL: WRONG-LIGHT (applies=true). Only kernel-adjacent content is one asserted sentence ("A context switch carries the same list."); no S-mode handler, syscall, scheduling, or OS memory management described/reasoned. Because invents a "leak from one thread into the next" argument the post never makes. Recommend dimming.
## the-allocator-that-keeps-its-books-in-the-empty-shelves — clean (5 OK)
## the-variable-that-is-not-the-same-variable — clean (5 OK). Minor: KERNEL because's "(worker 5, main 0)" errno run detail not in post body (verdict OK).
## the-descriptor-that-belongs-to-no-process — clean (5 OK)
## the-six-instructions-that-run-before-yours — clean (5 OK)
