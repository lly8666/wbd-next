# M0 R1 crypto dependency lock — coordinated main contract (2026-10-14)

Role: M0 active main / registry revision2 epoch1. Atomic ID: R1-M0-CRYPTO-DEPS-001.

## Why / prior state
M0 seq22 checkpoint e0679be8→HEAD 12827b1 only cursor-only H, governance38543577353 SUCCESS/CLEAN (not product pass). Four roles remain active. M3 head4776cc2 seq2 has no real Rust authenticated Seal/Open or 8-byte HP. The M3-authored coordination request in its work branch is `docs/devlog/M3/M0-REQUEST-AEAD-AND-ORACLE.md`. M0 already filled native pinned old-Go pathmtu oracle gap at main SOURCE e8599f7. M4 has advanced to seq4 independently; no worker ref was moved by M0.

## What is locked and why
M0 owns the root workspace-version source, the canonical Cargo.lock and static checker. `wbd-codec`'s **Cargo.toml only** gets `workspace=true` declarations as a cross-module G2 manifest coordination step; no M3 code or tests are claimed as authored by M0. Actual record implementations and vector proof stay with M3.

- `aws-lc-rs =1.18.1`, `default-features=false`, `non-fips,alloc`: explicit nonce `LessSafeKey`, separate tag in-place; no random nonce API or TLS record API substituted.
- `chacha20 =0.9.1`, `aes =0.8.4`: independent raw stream/block primitive for **8B** header protection. QUIC 5B HP API is prohibited.
- `aws-lc-sys` is pulled transitively; Linux native needs C compiler. Cross Win GNU and ARM64 are compile-only unless actually tested; Windows native runtime is NOT_RUN. Record wire format still outer5+PN8+AEADtag16+inner(kind/marker)2 =31 overhead; Go's exact sample, AAD/nonce, crypto outputs and C01-C04 remain to be validated by M3, not these probes.
- License review: aws-lc-rs ISC AND (Apache-2.0 OR ISC), sys dependency has compound AWS-LC/third-party notices; no assertion of final redistributable license clearance. RustCrypto AES and ChaCha20 dual MIT/Apache-2.0. Re-review transitive license manifest for redistribution.

## Actual validation and initial failure
First probe SOURCE 5f4c755 run38545556252 **FAILED** (Rust test harness E0382 consumed `Nonce` reused in the decrypt smoke). Third-party packages resolved and native AWS-LC compiled; no library compatibility PASS claimed. Correction SOURCE **6b39093225fe7400af70c6847cb260b2b6769371** rebuilt from scratch in GitHub Actions [38545741173](https://github.com/lly8666/wbd-next/actions/runs/38545741173) attempt1: Rust1.85.1, five real compiled-once API smokes (three AEAD explicit-nonce roundtrips and two HP 8-byte primitive invocations) native PASS 5/5, build/consumer separate with hash verification. Built root Cargo.lock emitted by that SOURCE/run; M0 copied exact generated lock, **not manually invented versions/checksums**.

**Gate for this commit and cursor acknowledgement:** same integrated main SOURCE must pass `r1-crypto-deps` build+consume plus existing R0 native/ABI/cross+static audit, not merely a permit file. If any fail retain precise source/run and repair only real blocker; no mixing SUCCESS from different sources into E2E qualification.

## Scope / next single atom
M0 root dependency/lock pin approval only. Original Go oracle M0 pathmtu at its separate SOURCE, M3 FrameBudget Rust at SOURCE3aa121e4, and new crypto API probe at SOURCE6b3909 do **not** combine into product pass. M3 must sync main root Cargo/lock before implementing genuine codec `LaneTxCrypto`/`LaneRxCrypto` and C01-C04 old Go differential wire+tamper+PN and 8B HP; worker retains all real crypto implementation ownership. M1 owner, M4 driver, M2 receipt remain independent. After M3 real S/H and worker integration available, M0 same-SOURCE Actions native in-process Normal/FEC off first packet. Production V4 DISABLED, Rust E2E/perf/physical NOT_RUN; no config/CLI/GUI change (internal dependency-only).


## Observed postscript — exact original failure and cross-toolchain fix

At integrated SOURCE [1ae49bd](https://github.com/lly8666/wbd-next/commit/1ae49bd644a4624db331c80d2dce6a8d181189e0), 14/15 Actions were SUCCESS including static audit, native ABI and native crypto API smoke; the [cross ABI run 38546166970](https://github.com/lly8666/wbd-next/actions/runs/38546166970) was **FAILED**, specifically Windows GNU `aws-lc-sys` could not find NASM. ARM64 build had passed. This failure is retained.

M0-only workflow toolchain correction [f2a7a84](https://github.com/lly8666/wbd-next/commit/f2a7a84dd8985e80964dac8b65e7b92652a07e8e) adds `nasm` only to Windows GNU CI build prerequisites. [Cross ABI Actions 38546390977](https://github.com/lly8666/wbd-next/actions/runs/38546390977) now verified SUCCESS for both ARM64 and Windows GNU **compile, C ABI link, build artifact hash, separate consume and static target inspection**; native execution of these cross targets remains NOT_RUN. Same-source governance38546390961 SUCCESS. Source `f2a7a84` differs from `1ae49bd`, so **do not assemble 14 old green + new green into a same-SOURCE qualification**. This atom approves the pinned manifest/lock and independently observed cross-toolchain repair, but it cannot claim Rust business wire compatibility or entire-product PASS.

Definitive receipts: `docs/evidence/M0/R1-crypto-dependency-lock.json`. M0 did not touch M3 or any worker branch. Stable pinned versions must be brought to M3 using its legal branch sync process; M3 crypto implementation is still owned by M3, not by this M0 probe.
