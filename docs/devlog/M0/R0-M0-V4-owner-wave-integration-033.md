# M0 next-wave integration and acceptance checkpoint (2026-10-15)

Baseline main CODE 2f8b2c900a0bd086b21a32448fb6462c8432824b and main governance run38696580565 SUCCESS. M2 final worker H014d636e seq15 Governance38692656343 SUCCESS. Prior CODE sources for all M1–M4 imported into main without changing workers or their role paths. Integration commits: M2 a8e5a77, M1 002b388, M4 2a1c578, M3 a387d1bb. Worker-native counts M2 51/51, M1 80/80, M4 71/71, M3 Debug98/98.

Source-locked M0 main tests: R2 native38691506375 SUCCESS; M1 owner wake/STOP38691375348 SUCCESS; M4 real Linux kernel 71+6 native38691637699 SUCCESS; main M3 G2/native codec38695199065 and link/record/fec-on PASS. Root generic Release accidentally ran the dedicated 24-row benchmark, causing timeout. Main CODE616fa8b quarantines Release-only benchmark using cfg_attr(ignore); CODE2f8b corrects actual count 97 PASS + 1 ignored. Identical source/compiled-once tests38696580529 and38696580521 both SUCCESS; artifacts/sha digests in JSON.

Real Go V4 protected transaction source09a7bd now explicit PrepareTransition then protected reply then DetachTransition then Go-only finish(true), with defer abort. Actual Go TLS11/11 on dd9c4b run38695761347 SUCCESS, including nonce failure rollback and retry. NOT a Go-to-Rust authenticated owner or product ABI.

M3 separate Release38685587150 completed 24/24 but 22/24 CPU timing rows violate CPU <= wall*1.02 due /proc clock outside wall measured interval; relative CPU ratios NOT_QUALIFIED. Next M3 task 015 fixes timing with fresh SOURCE and separate explicit Release. Prior failed/cancelled Actions remain as historical evidence, not hidden.

Main registry rev2 epoch1 code e88a6a formally assigned M1 bounded early RX010, M2 positive-RACK reindex008, M3 CPU timing015, M4 actual UDP RX burst010. Its governance38696146850 and five-crate bootstrap38696146961 both SUCCESS. No worker branch permission/epoch change.

M0 own remaining critical work: genuine private Go protected snapshot -> Rust allocated generation owner, rx/tx sequence ownership, early bounded queue, B01-B04 Stop/lease; current Rust untrusted cold 248-byte grammar cannot mint authentication. Production ABI capabilities remain 0, real positive raw/WinARM/500Mbps/physical all NOT_RUN.
