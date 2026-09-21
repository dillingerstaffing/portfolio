# Layer-lights audit, 42 posts

Read-only audit, 2026-09-21. Sources: `data/articles.json` layers dicts (5 slots each: ALGORITHM, FIRMWARE, ISA, KERNEL, MICROARCH) versus the canonical post prose extracted to `hidden_audit/bodies/<slug>.txt`. No files were modified.

Verdict key per slot: OK (verdict and because accurate), WRONG-LIGHT (lit but not earned by post content), WRONG-DIM (dimmed but earned), PARTIAL (post works at a layer that is unlit), BECAUSE-MISMATCH (verdict right, justification wrong or generic).

Bar applied: a light is earned only when the post genuinely describes, implements, measures, or reasons about the layer. A passing mention does not earn a light. The `because` text must be specific to the post's actual content.

## Per-post verdicts: posts with defects (15)

### the-receipt-for-the-bit-that-fell-off
- FIRMWARE: **WRONG-LIGHT**, applies=true. The post is a pure ISA flag-contract verification ("A bare-metal module ran a single fadd.d"); it never describes M-mode, boot, mstatus, or FS operations (grep: only the word "bare-metal" appears once, as environment context). Because claims "it reads the boot mstatus, moves FS from Off to Initial before the first floating-point instruction (with FS Off an FP instruction raises illegal-instruction), and the trap counter stays 0 across both phases" — none of that is in the post.
- KERNEL: **WRONG-LIGHT**, applies=true. The word "kernel" never appears in the post; the no-trap discipline is discussed as an ISA design choice ("which is why the ISA chose a no-trap discipline for these flags"). Because invents "the kernel's contract with user space."
- ALGORITHM: OK, applies=false. Kahan summation is a named customer, never computed.
- ISA: OK, applies=true. "the inexact add left (fcsr & 0x1f) == 0x01: NX set, and NV, DZ, OF, and UF all clear" — genuine F-extension contract verification.
- MICROARCH: OK, applies=false. "Eighteen checks, zero mismatches, three byte-identical runs under QEMU 8.2.2" — no implementation reasoning.

### the-four-legal-ways-to-see-memory
- FIRMWARE: **WRONG-LIGHT**, applies=true. The post is a host-side C validator ("one checksum identical across the -O2, -O0, and sanitizer builds"); it never mentions firmware, boot, or M-mode. Because argues boot firmware is a consumer of the rule ("boot firmware is the layer that actually chooses a MODE when it brings the machine up") — a claim about who might use the rule, not content in the post.
- KERNEL: **WRONG-LIGHT**, applies=true. The post never mentions the kernel, the supervisor, S-mode, satp writes, or address spaces. Because attributes kernel behavior ("the supervisor kernel installs address spaces through satp") the post never discusses.
- ALGORITHM: OK, applies=true. "Agreement between two differently-shaped descriptions proves the rule, not shared code." — two independent computations of the same legality function cross-validated.
- ISA: OK, applies=true. "the oracle is a 16-row table transcribed by hand from the spec's Table 114, the document's own row text quoted in the comments."
- MICROARCH: OK, applies=false. Legality is an architectural constant; the post draws the spec's own legality-vs-support line.

### the-register-that-never-interrupts-you
- FIRMWARE: **WRONG-LIGHT**, applies=true. The post never describes M-mode, mstatus, FS transitions, or fcsr restore; the sole machine-level hint is the passing clause "with the FS gate open" ("Four modules, 65 checks, no mismatches, three byte-identical runs each on QEMU 8.2.2, with the FS gate open."). Because claims "the sequence reads the boot mstatus, moves FS from Off to Initial before any floating-point instruction, and restores fcsr to zero at the end" — none in the post.
- KERNEL: **WRONG-LIGHT**, applies=true. No kernel, context-switch, process, or user-space content; the post's only save/restore mention is about libraries ("saving and restoring it so one library does not leave the machine's rounding changed behind another's back"). Because invents a context-switch argument ("the kernel's context switch carries fcsr... frm must be restored so a process keeps its rounding mode").
- ALGORITHM: OK, applies=false. frm write-readback pairs are probe assertions, not a portable computation.
- ISA: OK, applies=true. "Encode it as 111 and you get DYN, meaning ask frm. Encode anything else and the instruction's own choice wins over frm, whatever frm says."
- MICROARCH: OK, applies=false. "The base ISA does not generate a trap when a floating-point exception flag sets; the F extension requires explicit checks of the flags in software." — architectural constants, nothing timed.

### the-alignment-the-page-table-demands-of-itself
- FIRMWARE: **WRONG-LIGHT**, applies=true. The word "firmware" never appears in the post. Because claims "the first page tables are built by hand in early boot code: a misaligned superpage entry in firmware's own mappings faults on first access" — a scenario the post never performs (nearest content is only "A stray bit in a hand-built entry would otherwise describe a region whose base the entry does not fully determine", a passing mention).
- KERNEL: **WRONG-LIGHT**, applies=true. The word "kernel" never appears in the post. Because claims "the kernel is the heaviest user of superpage mappings... its page-table code must keep the low PPN segments zero" — true about the world, absent from the post.
- ALGORITHM: OK, applies=true. "The code above builds the mask and tests the masked PPN. The oracle never builds a mask: it walks the 44-bit PPN field from the top down and faults the moment it finds a set bit below position nine times the level. Two constructions, same verdict, on thirty million pairs (30,000,063), zero disagreements."
- ISA: OK, applies=true. "The specification refuses, in its own sentence from the virtual-address translation process, section 4.3.2: if i > 0 and pte.ppn[i-1:0] is not zero, this is a misaligned superpage."
- MICROARCH: OK, applies=false. "with an FNV-1a checksum identical under -O0, -O2, and the sanitizers" — compiler-level check, not hardware behavior.

### the-division-that-isnt
- KERNEL: **WRONG-LIGHT**, applies=true. The post contains no kernel, user-space, context-switch, or fflags-polling content at all. Because claims "the no-trap discipline fixes the kernel's contract with user space... fflags is per-hart state the context switch must save and clear so one process's invalid never accuses another" — entirely invented.
- FIRMWARE: **BECAUSE-MISMATCH**, applies=true. The trap-counter witness is genuine machine-level work, but the because imports "reads the boot mstatus, moves FS from Off to Initial" from the sibling FS post; the body only says "the trap counter at zero" and never describes installing an M-mode trap handler or touching mstatus.
- ALGORITHM: OK, applies=false. "Fourteen checks proved three things at once: the operation admits it has no answer, the bit remembers that it happened, and the machine never stops." — hardware flag contract, no computation.
- ISA: OK, applies=true. "The NaN you get is always the canonical one, 0x7FF8000000000000 for a double: positive sign, all significand bits clear except the quiet bit, in the manual's own words." (Minor: because says the "fcsr triple 0x0 to 0x10 to 0x0"; the body states the 0x00-to-0x10 readback only.)
- MICROARCH: OK, applies=false. "Fourteen checks, zero mismatches, three byte-identical runs on QEMU 8.2.2."

### the-register-that-answers-in-readback
- FIRMWARE: **BECAUSE-MISMATCH**, applies=true. The M-mode discovery is genuine machine-level work ("The discovery ran in M-mode on purpose: a MODE write that sticks cannot fault anything there, because M-mode accesses are never translated."), but the because claims the module "records the boot word 0x0" and "restores satp before dropping to S-mode" — neither in the post.
- KERNEL: **BECAUSE-MISMATCH**, applies=true. The light is earned thinly via the module's own S-mode phase ("After the discovery the module dropped to S-mode, enabled Sv39, and read a canary, 0xc0ffee11deadbeef, stored with translation off, back through the active walk at its virtual address, bit-exact"), which is supervisor-level virtual-memory operation. The because's "how a kernel discovers which address schemes a hart will accept" extends it into a kernel-discovery claim the post never makes.
- ALGORITHM: OK, applies=false. Write-then-readback is a probe discipline, not a portable computation.
- ISA: OK, applies=true. "The privileged specification prescribes exactly this experiment in section 2.3.3: the range of supported values can be determined by attempting to write a desired setting and then reading to see if the value was retained."
- MICROARCH: OK, applies=false. "all on QEMU 8.2.2, which the module names plainly. Silicon gets its own say."

### the-most-honest-lie-in-c
- ALGORITHM: **WRONG-LIGHT**, applies=true. The post never describes, computes, or compares a computational method, data-structure strategy, or encoding algorithm. It reasons about compiler semantics ("The compiler proved the memory could never be read again, and under the as-if rule that made every store dead") and compares compiler codegen treatments of the same store sequence. Compiler-semantics analysis is not an ALGORITHM-layer operation; the because accurately describes the content but miscategorizes it as a layer.
- FIRMWARE: OK, applies=false. "I compiled two one-line functions this morning, gcc 13.2.0 at -O2 for rv64g, and read the disassembly." — compile-and-read only.
- ISA: OK, applies=true. "The volatile-pointer loop, cast through volatile unsigned char*, compiled to a real 32-iteration sb loop" — verified instruction sequences off the disassembly.
- KERNEL: OK, applies=true. "But the kernel was free to page that anonymous page out to the swap device at any point while the secret sat there, and page it back in when the process touched it next." — genuine OS kernel behavior plus the mlock/RLIMIT_MEMLOCK syscall contract. The because honestly scopes this to documented claims ("the firsthand bench work here remains compile-and-read, nothing was executed").
- MICROARCH: OK, applies=false. Compile-time instruction choices, nothing timed.

### the-comparison-that-leaves-no-trace
- KERNEL: **WRONG-LIGHT**, applies=true. The post's only kernel-adjacent content is a single asserted sentence ("A context switch carries the same list."); it never describes, implements, or reasons about kernel behavior (no S-mode handler, syscall, scheduling, OS memory management). Because builds a "no hidden compare result can leak from one thread into the next" argument the post never makes.
- FIRMWARE: OK, applies=true. "Here is the complete save list from a real M-mode trap entry, excerpted with the pattern intact (full source linked below)" — real machine-level trap entry.
- ISA: OK, applies=true. "blt t0, t1, less compares and branches in a single instruction; the verdict exists only in what the program counter does next."
- ALGORITHM: OK, applies=false. "When the verdict must outlive the branch, it gets a name." — where the verdict lives, not a computation.
- MICROARCH: OK, applies=false. No pipeline/timing content.

### who-writes-the-a-and-d-bits
- FIRMWARE: **WRONG-LIGHT**, applies=true. The only M-mode content is the phrase "ADUE, bit 61 of the M-mode CSR menvcfg, the Svadu extension." The because describes M-mode setup work — "it probes ADUE writability, grants the PMP entry, delegates the faults with medeleg, and flips ADUE on the S-mode ecall" — that appears nowhere in the post body.
- ISA: OK, applies=true. "Loads need A, stores need A and D, and the software side of the switch respects exactly that split." (Minor: because calls ADUE a "WARL field" — true and specific, but not stated verbatim in the post.)
- KERNEL: OK, applies=true. "The S-mode handler sets A and D in the entry, issues sfence.vma to make the update visible, and the retried store succeeds; the entry reads 0x200400c7."
- ALGORITHM: OK, applies=false. "The post asks who stamps the A and D bits: the hardware walker or the software handler." — who maintains bits, not a computation.
- MICROARCH: OK, applies=false. The only hardware claim ("QEMU 8.2.2 implements exactly this switch") is architected behavior, not implementation.

### the-bit-that-reads-execute-only-pages
- FIRMWARE: **WRONG-LIGHT**, applies=true. M-mode appears only as the spec's motivation paragraph ("MXR was conceived for M-mode routines emulating missing hardware features, misaligned loads and stores being the example"), not as work the post does. Because describes module setup ("building the Sv39 tables by hand, opening one PMP NAPOT entry, delegating the fault with medeleg bit 13, and mret-ing into S-mode") absent from the post body.
- ISA: OK, applies=true. "MXR is bit 19 of sstatus, and the whole mechanism is one CSR write: the hardware's load rule becomes readable or executable instead of readable."
- KERNEL: OK, applies=true. "after the handler advanced sepc past the instruction and returned, t0 was still zero"; "xv6 does exactly that: its vm.c maps kernel text with read and execute together."
- ALGORITHM: OK, applies=false. "one bit in sstatus rewrites the load rule from readable to readable or executable" — a hardware permission rule, computes nothing.
- MICROARCH: OK, applies=false. "this verifies QEMU 8.2.2's model of the rule, not silicon."

### the-twelve-bits-the-walk-never-touches
- FIRMWARE: **WRONG-LIGHT**, applies=true. The post contains zero firmware content (no M-mode, PMP, SBI, boot). Because describes "M-mode firmware builds Sv39 page tables" — work the post never does.
- ISA: OK, applies=true. "The privileged specification says it plainly in section 4.3.2: the page offset of the physical address equals the page offset of the virtual address" — verified on 60,331,824 cases.
- KERNEL: OK, applies=true. "Your xv6 walk() always descends to level 0, so every mapping it builds is exactly the 4 KiB case this formula covers."
- ALGORITHM: OK, applies=false (borderline but honest). "A page-table walk never rewrites the low bits of your address" — the post transcribes the ISA's fixed address-formation contract rather than a chosen mechanism; the because is specific to the post.
- MICROARCH: OK, applies=false. "The honest boundary: the lab proves the 4 KiB case. The megapage forms above are verified against the spec text, not yet against a differential oracle."

### the-gate-with-three-locks
- FIRMWARE: **WRONG-LIGHT**, applies=true. The post contains zero firmware content. Because claims "M-mode firmware builds the page tables: writing a PTE with W set and R clear bakes in a guaranteed fault" — work the post never does.
- ISA: OK, applies=true. "The questions, in the order the specification's walk step applies them" — the 96-combination R/W/X/U rule table.
- KERNEL: OK, applies=true. "a running kernel asks this question on nearly every memory access, millions of times a second, which is why the gate has to be cheap."
- ALGORITHM: OK, applies=false. "The reason the specification bans the encoding instead is the invariant it protects: every writable page is also readable" — transcribing the ISA rule table, not a portable mechanism.
- MICROARCH: OK, applies=false. "the honest boundary, stated in the lab: this proves the leaf verdict only. Not the valid bit, not the accessed and dirty bits, not physical memory protection, not silicon."

### the-four-bytes-the-trap-handler-skips
- FIRMWARE: **WRONG-DIM**, applies=false. The post's handler is M-mode bare-metal code operating on mepc/mcause/mtval, verified against "QEMU's M-mode model" ("the hardware writes the faulting instruction's address into the mepc register and jumps to your handler"). Machine-level work is FIRMWARE by definition; the slot should be lit. The because also misstates the layer by limiting it to boot code ("no boot-time firmware code is written").
- ISA: OK, applies=true. "the length hides in the lowest two bits of the first parcel: anything but 11 there is a 16-bit compressed instruction, and 11 starts the longer forms."
- ALGORITHM: OK, applies=false. Instruction-length handling is RISC-V machine specifics, not a portable computational method.
- KERNEL: OK, applies=false. "The xv6 kernel gets away with mepc += 4 after an ecall only because ecall has no compressed form" — a one-sentence comparative aside, not kernel reasoning.
- MICROARCH: OK, applies=false. No trap timing or pipeline discussion.

### the-width-the-program-never-asks-for
- FIRMWARE: **BECAUSE-MISMATCH**, applies=true. The light is earned: "At machine mode I had to set the VS bits in mstatus before any vector instruction would execute: the extension is gated even when present." But the because names "boot.S" and "mstatus.VS=0x600 (VS=Initial)" — neither the filename nor the value appears in the post body.
- ALGORITHM: OK, applies=true. "The loop re-asks every iteration and advances by whatever came back." — strip-mining as a portable loop idiom.
- ISA: OK, applies=true. "it writes back the vl you actually get" / "VLMAX, the most elements one instruction can touch, is the register width times the number of registers you group, divided by the element width."
- KERNEL: OK, applies=false. "I built one bare-metal binary this morning" — nothing runs under an OS.
- MICROARCH: OK, applies=false. "Zero changes to the binary on three different machines, because the program never once assumed the width."

### the-write-that-sleeps
- ALGORITHM: **BECAUSE-MISMATCH**, applies=false. The dim is honest (the tick-edge choreography is measurement craft, not an algorithm), but the because cites "the FNV-1a fold," which appears nowhere in the post (grep-confirmed). The rest of the because is accurate.
- FIRMWARE: OK, applies=false. "No one inside the kernel told the test the write slept. It proved the block from outside, with nothing but the uptime tick counter for a stopwatch."
- ISA: OK, applies=false. "Fill an xv6 pipe with exactly 512 bytes, the whole buffer, and write one more byte. The call does not return." — ISA-independent scheduling claim.
- KERNEL: OK, applies=true. "when the buffer is full, pipewrite wakes the reader and sleeps on its own nwrite channel, and the reader's piperead answers with a wakeup on that same channel when it drains."
- MICROARCH: OK, applies=false. "It comes back 40 ticks later, when the child finally drains the pipe" — scheduler time in whole ticks.

## Per-post verdicts: clean posts (27)

### its-a-trap
All 5 OK. A:false (control-transfer contract, not a computation); F:false (never leaves S-mode); I:true ("On the ecall the CPU records where you were (sepc gets the address of the ecall) and why you came (scause gets 8, the code for an environment call from user mode)"); K:true (uservec/usertrap/syscall S-mode material; minor: because's "timer interrupt drives preemption" clause is not in the post); M:false (no pipeline content). Becauses post-specific and accurate apart from the noted clause.

### the-allocator-that-keeps-its-books-in-the-empty-shelves
All 5 OK. A:true ("It returned c, b, a. The freelist is a stack: last freed, first allocated."); F:false ("I pointed xv6's page allocator at a 64 MiB arena this morning"); I:false (no encoding/ABI claims); K:true ("The allocator is 76 lines of C in kernel/kalloc.c, and it stores no metadata of its own."); M:false. Becauses accurate.

### the-variable-that-is-not-the-same-variable
All 5 OK. A:false ("Same name, same line of source, two different pieces of storage."); F:false (Linux userspace experiment); I:true ("lui a5,0x0; add a5,a5,tp; lw a4,0(a5)" and "mov %fs:0xfffffffffffffffc,%ecx" — TLS lowering fixed by the machine contract); K:true ("When a thread is born, the loader copies the entire template into fresh memory for it."); M:false. Becauses accurate (minor: K because's "(worker 5, main 0)" run detail not in the post body).

### the-descriptor-that-belongs-to-no-process
All 5 OK. A:false; F:false (Linux userspace under a stock kernel); I:false ("no instruction encoding, decoding, or extension behavior is exercised"); K:true ("pidfd_getfd(pidfd, targetfd, 0) asks the kernel to copy that process's descriptor into your table."); M:false. Becauses accurate.

### the-six-instructions-that-run-before-yours
All 5 OK. A:false ("Here is the complete ROM, six instructions" — fixed sequence, not computed); F:true ("OpenSBI parks the other three itself and waits for the operating system to start them."); I:true ("auipc t0, 0 # t0 = 0x1000, the ROM's own address"); K:false ("On QEMU's virt board with no firmware, every RISC-V hart wakes up at address 0x1000."); M:false. Becauses accurate.

### the-stack-frame-is-optional
All 5 OK. A:false ("Why does -O2 delete it? The optimizer proved three things: no address of any local is ever taken, the whole computation fits in registers, and the function is a leaf." — compiler frame budget, not a computational method); F:false (user-mode listings, program already loaded); I:true ("the ABI requires the stack pointer to stay 16-byte aligned at all times."); K:false; M:false. Becauses accurate.

### the-division-that-always-answers
All 5 OK. A:true ("Because div and rem are total functions, defined on every input pair, the edge case stops being special and becomes just another value to compute with."); F:false; I:true ("The quotient of division by zero has all bits set. The remainder of division by zero equals the dividend."); K:true ("x86's idiv, as I understand it, raises a divide-error fault on these inputs: the processor suspends your program and hands you to a trap handler" — the no-trap property reasoned about at the trap-path level); M:false (divider-circuitry rationale quoted from the manual, never measured). Becauses accurate.

### the-id-card-inside-your-cpu
All 5 OK. A:false (manual table lookup, not portable computation); F:true ("Because the firmware that reads it runs on chips it did not choose. One CSR read names the width, the alphabet, and the privilege modes, everything early boot needs before it can trust anything else."); I:true ("The extensions field is WARL, write-any-read-legal: clear a bit and that extension's instructions revert to their reserved behavior"); K:false ("Supervisor and user code must ask through environment calls, which means a hypervisor can present a different ISA than the silicon underneath." — a passing mention, correctly dimmed); M:false. Becauses accurate.

### the-eight-bytes-that-became-four
All 5 OK. A:false ("Eight bytes in, four bytes out, decided by a range check." — toolchain rewrite, not portable computation); F:false (relocation tables and psABI live in the ELF contract); I:true ("The RISC-V ELF psABI names the rule: an AUIPC plus JALR pair may be relaxed to a single JAL when the procedure sits within minus one mebibyte to plus one mebibyte minus two of the call site."); K:false; M:false. Becauses accurate.

### the-register-that-is-always-zero
All 5 OK. A:false ("A move is an add against x0, the register that always reads zero." — x0 contract semantics, not portable); F:false ("csrr a3, mstatus csrrs a3, mstatus, x0 -> 0x300026f3" — encoding idiom only); I:true ("Type mv a0, a1 and ask what the machine executes. There is no MOV instruction in the base ISA, not even an opcode for one. What runs is addi a0, a1, 0, encoding 0x00058513"); K:false; M:false. Becauses accurate.

### the-conditional-move-risc-v-finally-allowed-itself
All 5 OK. A:false ("The canonical lowering is worth seeing once. cond ? x : y becomes three lines: czero.eqz t0, x, cond / czero.nez t1, y, cond / or rd, t0, t1" — ISA-specific idiom); F:false; I:true ("czero.eqz a0,a1,a2 is 0ec5d533, czero.nez is 0ec5f533, one funct3 bit apart"); K:false; M:false (the only implementation story "arrives as a debated forum thread rather than a measured fact"). Becauses accurate.

### the-bridge-that-doesnt-translate
All 5 OK. A:false ("One instruction translates. The other transports." — FMV is a move, not a computation); F:false ("bare-metal binary" appears once as a passing mention); I:true ("FMV.X.D and FMV.D.X do not modify the bits being transferred; in particular, the payloads of noncanonical NaNs are preserved."); K:false ("that separation is why mstatus.FS exists at all, the two-bit receipt that lets the kernel skip saving thirty-two registers when the running code never touched them" — passing mention in service of an ISA point, correctly dimmed); M:false ("renamed pipelines" appears once, passing mention). Becauses accurate. This post is a model of honest dimming: three passing mentions, zero lights.

### the-fence-the-instruction-cache-never-sees
All 5 OK. A:false; F:false ("One honest footnote: none of my bare-metal labs has ever needed this instruction."); I:true ("a valid implementation may cache every fetchable byte at the earliest opportunity and never read main memory for instruction fetches again"); K:true ("Linux gave user space a system call for it: __riscv_flush_icache, in the kernel since 4.15 with a glibc wrapper since 2.27"); M:true ("The instruction eye may still hold the old bytes it fetched long ago... So the jump runs the old bytes." — split I-cache/fetch-engine behavior plus QEMU translation blocks as a software I-cache). Becauses accurate.

### the-bouncer-on-the-stopwatch
All 5 OK. A:false ("One bit decides whether a user process may know what time it is." — access-control invariant, not a computation); F:true ("Then it clears that one bit, drops to user mode again, and runs the same instruction." — written as M-mode firmware, owns mcounteren); I:true ("This time the machine traps with scause 2, illegal instruction, sepc pointing exactly at the rdcycle site"); K:false ("the module pins the S-level gate open, held set and read back as 0x1 before each phase, and wiggles only the M-level one" — S-mode only a conduit); M:false. Becauses accurate.

### the-return-with-nothing-to-return-from
All 5 OK. A:false; F:true ("medeleg was written 0 and read back 0, so the trap could not be delegated away from M-mode; it had to land where the handler was waiting"); I:true ("The formal Sail model of the privileged architecture writes the rule as a bare match: in user mode, sret goes straight to handle_illegal(). No conditions, no escape hatch."); K:true ("sret is the second half of the trap contract. When it executes, privilege is restored from sstatus.SPP, interrupt enable from SPIE, and the program counter from sepc."); M:false. Becauses accurate.

### the-switch-with-nothing-behind-it
All 5 OK. A:false; F:true ("Write 0x6000000000000000 to menvcfg, the M-mode environment configuration register, and read it back: 0x2000000000000000." — M-mode-only CSR); I:true ("The measurement is a WARL probe, and WARL is the whole method."); K:false ("That works until the operating system maps a device register as ordinary cacheable memory." — motivation only, correctly dimmed); M:false. Becauses accurate.

### the-signal-that-xv6-never-sends
All 5 OK. A:false; F:false; I:false ("the proof compares behavior against POSIX and the kernel source, never against the machine manual"); K:true ("if (pi->readopen == 0 || killed(pr)) { release(&pi->lock); return -1; }" — xv6 kernel/pipe.c vs Linux fs/pipe.c); M:false. Becauses accurate.

### the-two-bits-that-spare-the-kernel-thirty-two-saves
All 5 OK. A:false ("The module measured exactly the flip the kernel trusts: Initial to Dirty on a single instruction, sticky on the next"); F:true ("The module starts at boot and reads mstatus: 0xa00000000, with FS, the floating-point status field in bits 14:13, sitting at 0, Off."); I:true ("at Off, a floating-point instruction does not execute and get recorded, it raises an illegal-instruction exception instead"); K:true ("With FS, the trap handler reads one field and skips the spill when the answer is not Dirty."); M:false. Becauses accurate.

### the-alarm-that-will-not-leave-its-room
All 5 OK. A:false; F:true ("On a bare-metal RISC-V machine running M-mode firmware, one 64-bit MMIO write of mtime + 5000 ticks lands in the CLINT's mtimecmp register for hart 0 at 0x02004000."); I:true ("mideleg is a WARL register, write any value and read back a legal one, and on this machine bit 7 is read-only zero: writes of 0x0, 0x80, and 0x14c4 all read back 0x1444"); K:false ("The module dropped the hart to S-mode anyway and armed the timer 500 ticks out. Exactly one trap, in M-mode, mcause 0x8000000000000007, zero S-mode arrivals." — no kernel behavior exercised); M:false. Becauses accurate.

### the-bell-and-the-switch
All 5 OK. A:false; F:true ("M-mode firmware owns mie.MSIE; a supervisor kernel cannot touch it."); I:true ("The trap rule, from the privileged architecture's own text: interrupt i is taken when mstatus.MIE is set and both mie[i] and mip[i] are set."); K:false ("So its inter-processor interrupts arrive as supervisor software interrupts instead, raised through firmware's sbi_send_ipi." — one-pass context, correctly dimmed); M:false. Becauses accurate.

### the-bit-that-reroutes-a-trap
All 5 OK. A:false; F:true ("setting it is how the firmware gets out of the way."); I:true ("medeleg is an M-mode register with one bit per trap cause: when a bit is set, traps of that cause are delegated to S-mode instead of landing in M-mode."); K:true ("Phase two writes 0x200, reads back bit 9 set, and demands exactly one trap in the S-mode handler with scause = 9 and the supervisor's own resume address sepc at the same ecall." — the delegated trap is the kernel's syscall path); M:false. Becauses accurate.

### the-bit-that-survives-the-context-switch
All 5 OK. A:false; F:false (marking global / choosing ASIDs is kernel work, correctly dimmed); I:true ("Global mappings were devised to reduce the cost of context switches." / "failing to mark a global mapping as global merely reduces performance, whereas marking a nonglobal mapping as global is an error." — the spec's own contract); K:true ("The kernel is mapped at the same virtual addresses in every process, and every context switch loads a new satp register carrying a new ASID."); M:false (because honestly disclaims the 196.216 ns figure as a host-model artifact). Becauses accurate; the MICROARCH because is a model of honest dimming.

### the-brake-pedal-on-the-stopwatch
All 5 OK. A:false; F:true ("RustSBI's performance-monitoring documentation states it directly: from supervisor mode these counters can only be started, stopped, or configured through mcountinhibit."); I:true ("The privileged manual breaks that answer in one sentence: mcounteren decides only who may see the counters, and the counters keep incrementing even when nobody can read them."); K:false ("One write of 0x1 to the mcountinhibit CSR, setting its CY bit, and one thousand back-to-back reads of mcycle came back identical, every one of them 0x0, a delta of exactly zero." — decided by the CSR bit, no kernel loaded); M:false ("on QEMU 8.2.2 the frozen counter reads back as 0x0, which is the model's choice, not the spec's demand"). Becauses accurate.

### the-page-that-was-never-there
All 5 OK. A:true ("for (;;) { p = sbrk(PAGESZ); if (p == (char *)-1) break; pages++; } p counts the pages the kernel agreed to" — grow-until-refusal as a portable capacity-finding protocol); F:false; I:false ("On a 128 megabyte QEMU machine the answer came back as a measured number: 32,468 pages, 132,988,928 bytes, about 126.8 megabytes." — a kernel count, not a machine contract); K:true ("sbrk(n) calls sys_sbrk(n, SBRK_EAGER). The syscall calls growproc, growproc calls uvmalloc, and uvmalloc calls kalloc once per page" — the -1 traced to kalloc's empty free list); M:false. Becauses accurate.

### the-multiply-with-no-multiply
All 5 OK. A:true ("for each set bit i of one half, add the other half shifted left by i into a 32-bit accumulator" — schoolbook expansion proved over all 4.3 billion pairs); F:false; I:true ("Base RISC-V, RV32I, has no multiply instruction. The mul instruction lives in the M extension, which is optional"); K:false; M:false ("Best of five at -O2: 47.232 nanoseconds per value, the timing honestly including the random-input step" — explicitly a timing ceiling, not a microarch claim). Becauses accurate.

### the-ten-fields-in-one-word
All 5 OK. A:true ("The lab decodes with shift-and-mask identities instead: one shift and one mask per field, every boundary explicit in the source"; "The mechanism is portable to every ISA; only the boundaries come from the RISC-V contract"); F:false ("the decoder configures no trap vector, CSR, or privilege level"); I:true ("The layout is the privileged specification's own: 44 bits of physical page number in bits 53:10, two bits reserved for supervisor software in 9:8, then the eight flags"); K:true ("Every page fault your kernel will ever handle starts with exactly this parsing step: xv6's walk() reads each level's entry to pull out the page number and check the permission bits"); M:false ("so the 9.626 number is the best observed, not a promise"). Becauses accurate.

### the-bit-that-remembers-who-called
All 5 OK. A:false; F:true — the ONLY post in the audited family whose body actually contains the M-mode setup work ("M-mode delegated supervisor ecalls to S-mode with medeleg bit 9, opened the whole address space with one PMP NAPOT entry, and dropped into an S-mode payload through sret"), so this FIRMWARE light is the earned reference; I:true ("SPP is bit 8 of sstatus, and the hardware writes it at the instant of the trap: the privilege mode the hart was in just before the trap"); K:true ("In usertrap(), near the top of the function: if ((r_sstatus() & SSTATUS_SPP) != 0) panic(\"usertrap: not from user mode\")"); M:false. Becauses accurate.

## Cross-post consistency violations

### 1. FIRMWARE boilerplate: seven unearned lights, one earned (FP and page-table lab family)
`the-bit-that-remembers-who-called` is the only post whose body actually performs M-mode setup (medeleg bit 9, PMP NAPOT, sret into S-mode), and its FIRMWARE light is earned. The same because language — mstatus reads, FS Off-to-Initial transitions, hand-built Sv39 tables, PMP NAPOT entries, medeleg bits, mret/sret into S-mode — appears in the FIRMWARE because texts of `the-receipt-for-the-bit-that-fell-off`, `the-register-that-never-interrupts-you`, `the-division-that-isnt`, `the-bit-that-reads-execute-only-pages`, `the-twelve-bits-the-walk-never-touches`, and `the-gate-with-three-locks`, but none of those six post bodies contains that work. Same lab family, same kind of content (bare-metal module + CSR readbacks), opposite verdicts: 1 correctly lit, 6 wrongly lit. The because texts were evidently written from a shared module-family narrative rather than from each post's body. The one post in the same family that demonstrably does describe the work (`the-two-bits-that-spare-the-kernel-thirty-two-saves`: "The module starts at boot and reads mstatus: 0xa00000000") is correctly lit, which sharpens the contrast.

### 2. FIRMWARE: earned-and-lit vs earned-and-dimmed
`the-four-bytes-the-trap-handler-skips` is dimmed on FIRMWARE while its handler is M-mode bare-metal code on mepc/mcause/mtval, verified against "QEMU's M-mode model." Meanwhile `the-return-with-nothing-to-return-from` (medeleg=0 M-mode handler, mcause/mepc/mtval/mstatus recording) and `the-bouncer-on-the-stopwatch` (M-mode experiment owning mcounteren) are lit and earned. Same content kind — M-mode trap-handler labs — opposite verdicts. Worse, the four-bytes because ("no boot-time firmware code is written") narrows the layer to boot code, while the earned lights correctly treat FIRMWARE as machine-level work.

### 3. KERNEL: the "kernel as consumer" invention pattern
Five posts light KERNEL with because texts that argue a kernel or context switch would consume the verified property, while the posts never mention one: `the-division-that-isnt` ("fflags is per-hart state the context switch must save and clear"), `the-register-that-never-interrupts-you` ("the kernel's context switch carries fcsr"), `the-four-legal-ways-to-see-memory` ("the supervisor kernel installs address spaces through satp"), `the-receipt-for-the-bit-that-fell-off` ("the kernel's contract with user space"), and `the-comparison-that-leaves-no-trace` ("no hidden compare result can leak from one thread into the next"). In each case the because answers "who might care" instead of "what the post does." Contrast with posts where the kernel half is genuinely worked: `its-a-trap` (uservec/usertrap/syscall), `the-allocator-that-keeps-its-books-in-the-empty-shelves` (kalloc.c), `the-signal-that-xv6-never-sends` (kernel/pipe.c), `the-write-that-sleeps` (pipewrite/piperead channels). Two posts also get the because half-wrong while the verdict is right: `the-register-that-answers-in-readback` (light earned thinly by its own S-mode canary read, but because claims it is "how a kernel discovers"), and `the-width-the-program-never-asks-for` (light earned by the mstatus VS gate, but because names a "boot.S" and "0x600" value absent from the post).

### 4. ALGORITHM: compiler semantics treated as a computational method
`the-most-honest-lie-in-c` lights ALGORITHM for the "portable optimizer contract" (as-if rule, dead-store deletion, compiler barriers). But `its-a-trap`, which also reasons about a contract (the trap contract), honestly dims ALGORITHM; so do `the-conditional-move-risc-v-finally-allowed-itself` (an ISA-specific lowering) and `the-twelve-bits-the-walk-never-touches` (transcribing the ISA's rule table), each on the explicit grounds that ISA-bound reasoning is not a portable computational mechanism. The same bar applied to the C post fails it: as-if reasoning is compiler/language semantics, not a described, computed, or compared computational method. (Where ALGORITHM is lit, it is earned: `the-multiply-with-no-multiply`'s schoolbook expansion, `the-page-that-was-never-there`'s grow-until-refusal protocol, `the-ten-fields-in-one-word`'s portable shift-and-mask identities, `the-division-that-always-answers`'s total-function edge-case contract, `the-width-the-program-never-asks-for`'s strip-mining idiom, `the-alignment-the-page-table-demands-of-itself`'s dual-construction cross-validation.)

### 5. Honest-dim models that prove the bar is attainable
Several posts demonstrate what correct grading looks like and were used as calibration: `the-bridge-that-doesnt-translate` correctly dims three layers despite passing mentions ("bare-metal binary", mstatus.FS lazy-save, "renamed pipelines"); `the-bit-that-survives-the-context-switch` explicitly disclaims its own timing figure as a host-model artifact; `the-four-bytes-the-trap-handler-skips` is the exception that proves the FIRMWARE rule (should be lit, see violation 2).

## Defect rollup, ordered by severity

### A. Partial lights: post works at a layer that is unlit — none found as a distinct case
No post was found where an earned layer is dimmed alongside other lit layers, other than the single WRONG-DIM below (which is that exact pattern and is listed first per the user's severity ordering).

### B. Wrong dims: 1
1. `the-four-bytes-the-trap-handler-skips` / FIRMWARE — dimmed, but the post's handler is M-mode bare-metal code (mepc, mcause, mtval, "QEMU's M-mode model"). Its because also misstates the layer by limiting it to boot code. Correct: applies=true, with a because that names the actual M-mode handler work.

### C. Wrong lights: 15 slots across 11 posts
1. `the-receipt-for-the-bit-that-fell-off` / FIRMWARE — lit; no M-mode, boot, mstatus, or FS content in the post; because describes absent module-source setup.
2. `the-receipt-for-the-bit-that-fell-off` / KERNEL — lit; word "kernel" never appears; because invents "the kernel's contract with user space."
3. `the-register-that-never-interrupts-you` / FIRMWARE — lit; only firmware-adjacent mention is the passing clause "with the FS gate open"; because describes absent mstatus/FS/fcsr setup.
4. `the-register-that-never-interrupts-you` / KERNEL — lit; no kernel, context-switch, process, or user-space content; because invents a context-switch argument (post's save/restore is about libraries).
5. `the-four-legal-ways-to-see-memory` / FIRMWARE — lit; host-side C validator, never mentions firmware/boot/M-mode; because argues firmware is a consumer of the rule.
6. `the-four-legal-ways-to-see-memory` / KERNEL — lit; never mentions kernel/supervisor/S-mode/satp; because attributes absent kernel behavior.
7. `the-division-that-isnt` / KERNEL — lit; no kernel, user-space, context-switch, or fflags-polling content; because invents a full context-switch argument.
8. `the-alignment-the-page-table-demands-of-itself` / FIRMWARE — lit; word "firmware" never appears; because describes early-boot page-table setup the post never performs.
9. `the-alignment-the-page-table-demands-of-itself` / KERNEL — lit; word "kernel" never appears; because describes kernel page-table code absent from the post.
10. `the-bit-that-reads-execute-only-pages` / FIRMWARE — lit; M-mode appears only as the spec's motivation paragraph; because describes absent module setup (Sv39 tables, PMP NAPOT, medeleg bit 13, mret).
11. `the-twelve-bits-the-walk-never-touches` / FIRMWARE — lit; zero firmware content in the post; because describes absent firmware page-table building.
12. `the-gate-with-three-locks` / FIRMWARE — lit; zero firmware content in the post; because describes absent firmware page-table building.
13. `the-comparison-that-leaves-no-trace` / KERNEL — lit; only kernel-adjacent content is one asserted sentence; because invents a leak-across-threads argument.
14. `the-most-honest-lie-in-c` / ALGORITHM — lit; post reasons about compiler semantics, never describes/computes/compares a computational method; because miscategorizes the content as the ALGORITHM layer.
15. `who-writes-the-a-and-d-bits` / FIRMWARE — lit; only M-mode content is the phrase "the M-mode CSR menvcfg"; because describes M-mode setup (ADUE probing, PMP grant, medeleg delegation, ADUE flip) nowhere in the post.

### D. Because mismatches (verdict right, justification wrong or generic): 5
1. `the-division-that-isnt` / FIRMWARE — because imports "reads the boot mstatus, moves FS from Off to Initial" from the sibling FS post; body only says "the trap counter at zero."
2. `the-register-that-answers-in-readback` / FIRMWARE — because claims the module "records the boot word 0x0" and "restores satp before dropping to S-mode"; neither in the post.
3. `the-register-that-answers-in-readback` / KERNEL — because frames the S-mode canary read as "how a kernel discovers which address schemes a hart will accept"; the post ascribes the discovery to its own bare-metal module.
4. `the-width-the-program-never-asks-for` / FIRMWARE — because names "boot.S" and "mstatus.VS=0x600 (VS=Initial)"; the post only says the VS bits in mstatus were set at machine mode.
5. `the-write-that-sleeps` / ALGORITHM — because cites "the FNV-1a fold," which appears nowhere in the post (grep-confirmed).

Minor because notes (verdicts still OK, not counted as defects): `its-a-trap` KERNEL because includes a "timer interrupt drives preemption" clause not in the post; `the-variable-that-is-not-the-same-variable` KERNEL because includes a "(worker 5, main 0)" errno run detail not in the post body; `who-writes-the-a-and-d-bits` ISA because calls ADUE a "WARL field" (true, not stated verbatim); `the-division-that-isnt` ISA because describes a "0x0 to 0x10 to 0x0 triple" while the body states a single 0x00-to-0x10 readback; `the-width-the-program-never-asks-for` KERNEL because mentions a "-bios none" QEMU detail not named in the body.

## Totals
- Posts audited: 42 (210 slots)
- Posts with defects: 15
- Posts clean: 27
- Wrong lights: 15 slots across 11 posts
- Wrong dims: 1 slot
- Because mismatches: 5 slots
- Partial lights (earned-but-unlit): 0 as a distinct class (the one under-lit case is the wrong dim above)
