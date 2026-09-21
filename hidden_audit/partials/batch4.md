# Batch 4 findings (worker completed 2026-09-21 02:20 EDT)

## the-division-that-isnt — 2 defects
- FIRMWARE: BECAUSE-MISMATCH (applies=true; trap-counter witness is genuine machine-level work). Because imports mstatus read and FS Off-to-Initial steps from the sibling FS post; post never describes them. Body only says "the trap counter at zero".
- KERNEL: WRONG-LIGHT (applies=true). Post contains no kernel, user-space, context-switch, fflags-polling content. Because invents kernel contract argument. Minor: ISA because mentions "0x0 to 0x10 to 0x0 triple"; body states 0x00 to 0x10 readback only.
## the-switch-with-nothing-behind-it — clean (5 OK)
## the-signal-that-xv6-never-sends — clean (5 OK)
## the-register-that-never-interrupts-you — 2 defects
- FIRMWARE: WRONG-LIGHT (applies=true). Post never describes M-mode, mstatus, FS transitions, fcsr restore. Only machine-level hint is the passing clause "with the FS gate open". Because describes absent content.
- KERNEL: WRONG-LIGHT (applies=true). No kernel, context-switch, process, or user-space content. Because invents context-switch argument (post's save/restore mention is about libraries).
## the-four-legal-ways-to-see-memory — 2 defects
- FIRMWARE: WRONG-LIGHT (applies=true). Host-side C validator; never mentions firmware/boot/M-mode. Because argues firmware is a consumer of the rule, not what the post does.
- KERNEL: WRONG-LIGHT (applies=true). Never mentions kernel, supervisor, S-mode, satp, address spaces. Because attributes absent kernel behavior.
## the-register-that-answers-in-readback — 2 defects (verdicts right, becauses wrong)
- FIRMWARE: BECAUSE-MISMATCH (applies=true; M-mode discovery is genuine machine-level work). Because claims module "records the boot word 0x0" and "restores satp before dropping to S-mode"; neither in the post.
- KERNEL: BECAUSE-MISMATCH (applies=true; S-mode canary read through the active walk is thin-but-real supervisor VM operation, so the light is earned). Because frames it as "how a kernel discovers" which the post never says.
## the-two-bits-that-spare-the-kernel-thirty-two-saves — clean (5 OK)
