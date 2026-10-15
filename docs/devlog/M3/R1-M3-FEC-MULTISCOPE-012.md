# R1-M3-FEC-MULTISCOPE-012 — two tunnels / both directions under fake monotonic time

M0 formal main registry rev2 epoch1 assignment: verify no cross-scope authenticated-input FEC replay/BlockID/Heavy→Compact→Retired pollution. The legacy Go V4 authenticated origin does not exist in M3. Positive FecOrigin is strictly #[cfg(test)], and production remains default denied.

Test-only code SOURCE `4787d94617afe72c511f3f2299d1b060c2930c6c`: two M3-owned codec files changed, `fec_multiscope_tests.rs` and LINK-subtree R1-only test mount. **No production algorithm modification** and no root Cargo, ABI, workflow, registry or Go exporter edits.

Native compiled-once Linux x64 Rust1.85.1 [worker run38674583861](https://github.com/lly8666/wbd-next/actions/runs/38674583861): **94/94 r1_ PASS** (9 new + 85 prior), binary SHA256 `8f1a5392c71eb266f94a9c3c4f63e1eccf7313a8963129fe6892d1e02f252234`, log SHA256 `6c2edda547ff5050a2b1ed47a8dcef09af4fb006ca2ff9e9668c0d778ba28125`. Seven same-SOURCE workflow runs SUCCESS including R0 Go LINK/FEC, framing, G2 and [own Governance38674583957](https://github.com/lly8666/wbd-next/actions/runs/38674583957) **attempt3 SUCCESS**.

Governance attempts1 (job116225157669) and2 (job116225732758) failed `ROLE_SCOPE_FAILED: control or source moved mid-audit` because M0 main concurrently advanced. M3 worker SHA stayed `4787d94617afe72c511f3f2299d1b060c2930c6c`; no code or permissions changes and no silent failure removal. Third attempt job116226414225 passed.

Nine new real-record tests prove four simultaneously live tunnel+direction scopes can independently admit PN=0/BlockID=1; foreign true AEAD ciphertext cannot mutate peer PN even if mislabeled with target route; exact source with own keys first-delivers, duplicate refuses. One tunnel's callback expiry cannot retire peer; late genuine parity reopens neither retired peer nor a pressure-evicted source. Heavy/Compact caps 1 and four-byte cap force ID floor in only pressured owner. A rekeyed epoch+generation resets PN and admits new ID despite old source/parity ciphertext being cryptographically rejected; FFFFFFFF to one requires explicit generation. Pinned old-Go 56B FEC source fixture still passes under independent real AEAD lanes; unbound origin denies before decrypt.

Full evidence `docs/evidence/M3/R1-M3-FEC-MULTISCOPE-012.json`. **No production V4 handshake/session-origin construction, transport packet integration, Windows/ARM native, ISA-L/SIMD, performance or physical proof**. Evidence S and cursor-only H require independent Governance.
