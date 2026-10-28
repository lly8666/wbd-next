# PLAN026 Rust raw RX SO_RCVBUF: real 100Mbps scoped PASS, controlled 150Mbps next

Original user requested high rate Rust-only kernel loss RCA with additional bounded buffer headroom. The product change `crates/wbd-platform/src/linux_raw_carrier.rs` sets only an OS-owned IPPROTO_TCP RAW RX socket `SO_RCVBUF` request4MiB, reads `getsockopt` effective bytes and records any kernel clamping. No host-global sysctl, fq600, Windows Rust owner, ARQ, FEC code or crypto was modified. Prior unchanged Linux guest default `rmem_default=212992` bytes, `rmem_max=4194304`.

## Actual first source-qualified product regression

New true compiled product SOURCE `0abd1b04ee7a39d8aa426963564a079523c1036a`, Action [40681039919](https://github.com/lly8666/wbd-next/actions/runs/40681039919), artifact `12813077746`, locally verified ZIP SHA256 `014a0cef822ba57f27b200df86a6641e7d1898f6a1b892ddb1825c907882e9c5`. Source 100Mbps scene `a09aa5cc9668515c3e6edfe91b2af2e421541c1ca7aac46e57baba02eb59c1a3`. FULL fresh Linux Rust+original TLS server, Windows EXE and Rust DLL built and source-manifest SHA-checked, signed Npcap/Wintun real, WSL2 Linux real. All compile and unit preflight gates PASS, native Windows/Linux product+owned Stop PASS.

- Windows source app sent `823247` at **99.9732Mbps**, Linux app unique received `823247` at **99.9732Mbps**, **zero app missing in this direction**. Linux source app sent `822766` at **99.9154Mbps**, Windows app unique received `822665` at **99.9029Mbps**, **101 app missing**, first delivery 99.9877%. Strict both >=99.9% **PASS**, but not absolute bidirectional zero-loss.
- Native Linux server `WBD_LINUX_RAW_RX_RCVBUF requested_bytes=4194304 effective_bytes=8388608 kernel_capped=false scope=OWNED_RAW_RX_SOCKET`: verified **8MiB kernel effective** with no clamp. Actual server `/proc/<pid>/fd -> socket:[inode]` precise match at end: PID1005 `wbd-v4-server` owns **6895/9515/6901**; all **raw socket drops delta=0** and final RX queue0. Last original SOURCE0543 @100Mbps different VM had raw drops1800 and app missing1779.
- Linux bound UDP fixture socket drop0 and guest Udp RcvbufErrors0; actual real tc ifb netem pkt839201/drops0, eth0 pkt837842/drops0, overlimits0/requeues0. True original Rust server `raw_observed839267 data_unique824516 tun_udp824501 open_invalid0 tun_failed0`; counts include controls and lifecycle, not exact app measurement conservation.
- Business UDP **round-trip** p99 Windows610ms, Linux624.732ms; these are independent same-origin clocks, NOT cross-OS one-way p99. Windows generator CPU47.9219s, Linux53.5959s, no same-VM old/new CPU efficiency claim.

Verdict: **100Mbps 300ms/0% kernel-loss 60s Rust Normal/off performance scoped PASS**, real raw receive kernel drops0, both Stop pass. No physical or FEC/other mode claims. This proves the raw socket buffer headroom removed the measured Linux RX queue overflow **at 100Mbps on this host**, not that 150Mbps or absolute zero-loss is solved.

## One faster unchanged-product 150Mbps verification

Because user wants enough margin to cover higher load, run one genuine 150Mbps each direction, one-way300ms, 0% injected loss, 60s with exact original 96/288/1060/1200B packet mix, seed20261028, MTU1400, the *same already-built SOURCE0abd product*. Tag `[plan026-rust-rxbuf-reuse-150]` runs `scenarios/wl-normal-150m-300ms-0loss-60s.json` with prebuilt artifacts from original new-source build Action40681039919, pinned SHA `0abd1b04ee7a39d8aa426963564a079523c1036a`; independent fixed SHA manifests for Windows EXE/Rust DLL and Linux lib/peer, and diff guard rejects product changes since compiled source. It skips compilation only, **not** authenticated TLS, signed drivers, WSL2, genuine TUN/NPF, netem, 60s or owned Stop. This is distinct from older SOURCE0543 prebuilt 150 failure, and no old Go steady A/B is run.

Report exact offered each direction, unique first-delivered, full target>=95% offered, >=99.9% first-delivery both, raw server-owned socket drops delta, effective SO_RCVBUF marker8MiB, true tc drops and Stop. If 150mbps fails, record first source/queue stage instead of blindly raising another buffer size; consider native RX batch consumption/WSL2 schedule. Nothing here asserts 150 outcome before Action completes.

```feature-impact
{"kind":"none","ids":[],"reason":"Only source-scoped evidence, Linux raw-TUN feature catalog status for measured 100Mbps and source-verified reusable 150Mbps harness workflow; the actual Rust product change was already committed and qualified in SOURCE0abd."}
```
