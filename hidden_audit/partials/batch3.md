# Batch 3 findings (worker completed 2026-09-21 02:20 EDT)

## the-conditional-move-risc-v-finally-allowed-itself — clean (5 OK)
## the-receipt-for-the-bit-that-fell-off — 2 defects
- FIRMWARE: WRONG-LIGHT (applies=true). Post is pure ISA flag-contract verification ("A bare-metal module ran a single fadd.d"); no M-mode, boot, mstatus, FS content. Because ("reads the boot mstatus, moves FS from Off to Initial") describes absent content.
- KERNEL: WRONG-LIGHT (applies=true). Word "kernel" never appears; no-trap discipline discussed as ISA design choice, not kernel behavior. Because invents "the kernel's contract with user space".
## the-bridge-that-doesnt-translate — clean (5 OK). Passing mentions noted: "bare-metal binary" (firmware, passing), mstatus.FS lazy-save (kernel, passing), "renamed pipelines" (microarch, passing).
## the-fence-the-instruction-cache-never-sees — clean (5 OK)
## the-bouncer-on-the-stopwatch — clean (5 OK)
## the-write-that-sleeps — 1 defect
- ALGORITHM: BECAUSE-MISMATCH (applies=false, verdict right). Because cites "the FNV-1a fold" which appears nowhere in the post (grep-confirmed). Rest of because accurate.
## the-return-with-nothing-to-return-from — clean (5 OK)
