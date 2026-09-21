# Batch 6 findings (worker completed 2026-09-21 02:20 EDT)

## the-multiply-with-no-multiply — clean (5 OK)
## the-bit-that-reads-execute-only-pages — 1 defect
- FIRMWARE: WRONG-LIGHT (applies=true). Post never works at firmware level; M-mode appears only as the spec's motivation ("MXR was conceived for M-mode routines emulating missing hardware features"). Because describes Sv39 table building, PMP NAPOT, medeleg bit 13, mret: absent from post.
## the-twelve-bits-the-walk-never-touches — 1 defect
- FIRMWARE: WRONG-LIGHT (applies=true). Zero firmware content in post (no M-mode, PMP, SBI, boot). Because describes firmware page-table building absent from post.
## the-gate-with-three-locks — 1 defect
- FIRMWARE: WRONG-LIGHT (applies=true). Zero firmware content in post. Because describes firmware page-table building absent from post.
## the-ten-fields-in-one-word — clean (5 OK)
## the-bit-that-remembers-who-called — clean (5 OK). Note: the ONLY one of these whose body actually contains M-mode setup ("M-mode delegated supervisor ecalls to S-mode with medeleg bit 9, opened the whole address space with one PMP NAPOT entry, and dropped into an S-mode payload through sret"), so its FIRMWARE light is earned.
## the-four-bytes-the-trap-handler-skips — 1 defect
- FIRMWARE: WRONG-DIM (applies=false). Post's handler is M-mode bare-metal code (mepc, mcause, mtval, "QEMU's M-mode model"); machine-level work = FIRMWARE. The because also misstates the layer (narrows it to boot code). Corrected: true.
