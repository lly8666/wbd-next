# Windows Rust NPF borrowed-frame RX: single-runner ABBA decision

## Recovered evidence
Original compiled A source 7fc38591c501ff4a06e1862c7b08d5d3dbc1be95 passed true signed 150Mbps Windows/WSL2 run 40693430836, with 8.390625s whole Windows EXE CPU /74.437s. New borrowed-frame compiled B e6be9358d2272d7e1960a935be7fe772885bb034, Actions 40697876014, two attempts on DIFFERENT runners: first CPU51.25s, Windows first-delivery98.6538% FAIL; second CPU11.0s, first unique100% each PASS. Both prove removal of ~1.2GB full-frame Rust scratch memcpy but CANNOT isolate host variance. A retains the previous successfully qualified <=32 DATA/CONTROL RX to TX SetEvent wake coalescing. B adds only two native Rust files: engine RX callback and platform pcap_next_ex borrowed-slice API.

## Exact same-host A-B-B-A

Workflow tag [plan026-win-npf-abba-150] deliberately skips recompilation ONLY to use exact source-verified original already-built binary pairs, on ONE Windows-2025 runner/job, same signed Wintun/Npcap installation, same WSL2 Ubuntu guest, HyperV firewall and vEthernet. Real full original Go cold TLS control + Rust NativeOwner (NOT legacy Go steady state), packet path and both owned Stop execute independently for A1, B1, B2, A2, with full signed driver/WSL2 netem and true 60s UDP+TCP per leg.

Immutable binary origin:
- A from run40693430836 Windows artifact12817869276, Linux artifact12818806001, source7fc.
- B from run40697876014 attempt2 Windows artifact12821761652, Linux artifact12820257191, sourcee6be.

tools/m0_wl_native_abba_prepare.py pins artifact ZIP SHA256 and original GitHub run source identities, checks full Windows and Linux manifest source+per-binary SHA, and rejects ambiguous duplicate artifact names. The workflow verifies no product-path changes from compiled B to current harness SHA and only the TWO expected source changes from A to B. Each leg separately changes complete matching Windows EXE/DLL and Linux peer/lib after previous full Stop; driver, VM and scenario do not change. Same exact scenario sha e22a96fbd4d6de2b4dc581d7013b343e61f5775298480e185c7a5562906d516e, 150Mbps each, 300ms each one-way, 0% injected tc, 60s+drain and original 96/288/1060/1200B mix.

Per-leg allowlisted redacted logs and real Win32 GetThreadTimes/GetProcessTimes, unique first-delivery, CPU kernel/user, RTT, exact product source SHA, Linux raw socket inode owner/drop, Linux UDP app drops, actual tc qdisc drops, Stop proof reside in wl-native-abba/1-A,2-B,3-B,4-A and summary.json. No uploaded password, TLS key, original unredacted product logs, private WAL or packet payload. One leg with an unproven Stop aborts subsequent same-host launches; a delivered-packet gate failure does not hide evidence, and subsequent legs execute only after proved Stop.

## Strict precommitted decision

Every leg must actually offer >=142.5Mbps EACH direction, first unique deliver >=99.9% EACH, zero true kernel tc drops in both directions, zero owned Linux raw socket drops, zero Linux UDP fixture drops, original signed drivers and Stop both PASS. B any red => ROLL_BACK_B, even if lower CPU. A red but B both green => INCONCLUSIVE, never promote an apparent speedup on a broken baseline.

With all four PASS and measured CPU, normalize Windows EXE CPU seconds by first-delivered GB in both directions, compare mean(A1,A2) vs mean(B1,B2); ABBA cancels simple linear host drift. KEEP_B only if B uses >=5% fewer CPU-sec/GB, else ROLL_BACK_B. This is an engineering threshold, not statistical proof across different hardware. Per-thread actual TX/RX TIDs and kernel/user breakdown are separately retained, but CPU process includes original Go cold control and Rust DLL and excludes driver-wide ISR/DPC. Neither build's old-Go steady A/B is involved.

Rollback means restore ONLY the NPF borrow Rust product changes to qualified source7fc style, keep 32-record wake coalescing and Linux raw SO_RCVBUF; then rebuild resulting source and rerun exact signed native scenario. Source evidence does not authorize disabling driver memory lifetime or Stop safety simply because trusted environment.

```feature-impact
{"kind":"none","ids":[],"reason":"Source-locked same-Windows-runner A-B-B-A fixture and deterministic keep/rollback thresholds only; no Rust product change."}
```
