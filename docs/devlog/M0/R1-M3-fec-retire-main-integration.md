# R1-M0-M3-FEC-RETIRE-MAIN-010 · 2026-10-15

## Restored authority and code scope
M0 main initial H `f5be4d8da46d5d10ccd8617752287d57d2d68e16` seq46 checkpoint `a6f3ee2a248f11fb8c4dea6548044ddf0caa14ca` Governance38669100481 SUCCESS. Registry rev2, epoch1 and M1–M4 owners remain intact; workers independently advanced their own branches and M0 did not modify them.

M3 isolated code SOURCE `e8d62776ebf3258c038155f4637bd1524d6282b7` proved 75/75 native `r1_` tests in Actions38667240535 and worker cursor-only H `6fe26165` Governance38667890659 PASS. The worker and main codec diff was independently audited. We imported exactly worker blobs for `fec_rx.rs`, `link_fec_wire.rs` (test registration), and eight adversarial pressure tests `fec_retire_pressure_tests.rs`, without changing Cargo.lock or Go code.

## Counterexample and correct deadline model
Before fix, a late Heavy timeout callback incorrectly initialized Compact TTL from callback clock; a callback arriving after both 3-second Heavy and 10-second Compact TTLs therefore improperly kept tombstones for an additional 10 seconds. M3's fix calls `compact_heavy_at(id, original_heavy_deadline)` for timeout, preserving original first-source absolute boundary. Normal completion and capacity pressure still use owner clock. Native tests prove one late expire() can retire both, old parity/systematic does not resurrect, valid unrelated recovered business remains independent; tested across RS profiles, BlockID generation/direction/epoch/wrap, metadata conflict, memory pressure and old-Go 56B oracle. Authenticated context is TEST-SUPPLIED, not live Go V4 provenance.

First main code SOURCE `4aed5d5cc22393cbe5ec06e55b24f3f18d8bbeea` produced 12 GitHub Actions, 11 success including new FEC pressure native75/75 run38669864229, FEC-on3/3, full Linux kernel and codec old-Go tests. Existing r1-record-auth-replay run38669864304 **FAILURE** although actual Rust `r1_` 75/75 passed: old CI gate required exactly 67. This failure remains immutable, and must never be relabeled success.

Final CODE SOURCE **`260335486d4e3bfd4d50215f5840027e09fe94c9`** corrects old exact native count67→75 and adds source test file SHA, while coupling the two affected native workflows. Three GitHub Actions on that exact source ALL SUCCESS:
- [r1-record-auth-replay38670039101](https://github.com/lly8666/wbd-next/actions/runs/38670039101) Rust native 75/75, compiled once, consumer confirms exact source/binary hashes.
- [r1-fec-retire-native38670039058](https://github.com/lly8666/wbd-next/actions/runs/38670039058) same native75/75 including 8 new adversarial cases, independent build/consumer and SHA artfacts.
- [Governance38670039087](https://github.com/lly8666/wbd-next/actions/runs/38670039087) SUCCESS.

Full SHA artifacts and run IDs are in `docs/evidence/M0/R1-M3-fec-retire-main-integration.json`. This qualifies only native Rust authenticated-input pure FEC lifecycle behavior, not real Go session key/epoch/generation exporters, real AF_PACKET raw, Windows/ARM native, ISA-L acceleration, 500Mbps/p99, product or physical; authoritative product qualification remains NOT_RUN.

## Next
M0 next independent bounded integration: review and import M1 TX ready-batch or M4 Linux RX recvmmsg (now independently worker-qualified) into main with a new same SOURCE native syscall/full packet test. Prioritize authentication provenance and real raw data-plane prerequisites before enabling V4 product. Four worker branches continue on their own assigned atoms.
