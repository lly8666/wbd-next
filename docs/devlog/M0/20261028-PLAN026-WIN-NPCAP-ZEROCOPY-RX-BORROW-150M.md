# PLAN026 Windows Rust RX: in-place borrowed Npcap frame, no extra Ethernet memcpy

## Problem statement and measured starting point

The exact current compiled product `7fc38591c501ff4a06e1862c7b08d5d3dbc1be95`, [real native run40693430836](https://github.com/lly8666/wbd-next/actions/runs/40693430836), passed signed Npcap/Wintun/WSL2 two-way150Mbps Normal/off /300ms one-way each /0% netem loss /60s with both owned Stop, source-locked real Rust DLL and Linux peer. Its 74.437s Windows EXE process CPU was8.390625s (kernel4.875, user3.515625), actual RX worker TID6952 CPU lower bound6.42188s, TX TID8968 CPU lower bound1.46875s; sample **not** same VM A/B CPU attribution. Existing prior optimization made NPF RX→TX wake attempts39701 for1236151 accepted DATA records, ~31.14 DATA per wake; retain it.

Product `NpcapRx::read` calls `pcap_next_ex` then copies every received Ethernet caplen (up to `MAX_NPF_FRAME`) to a 65KiB Rust stack slab and invokes `ethernet_ipv4`/tuple parse/M3 AEAD/PN opening/Wintun delivery synchronously; its NPF capture data pointer was already valid through all that work. ~1.2 million packets of mostly 1060/1200B imply >1GiB of redundant memory traffic across 60s at target150Mbps; actual **bytes skipped** must be measured in the next run, not guessed. No evidence merits changing fq600, Go cold TLS, sender M2, TCP-looking wire or the FEC decoder.

## Official API review and design limits

[Official Npcap pcap_next_ex reference](https://npcap.com/guide/wpcap/pcap_next_ex.html) says the returned header/packet data pointer is owned by libpcap and **not guaranteed valid after the next `pcap_next_ex`, `pcap_next`, `pcap_loop`, or `pcap_dispatch`**. Therefore reading inside a synchronous callback *before any further capture API call* is permitted; storing the pointer/slice in a queue, sharing with another thread or letting an owned result retain its lifetime is not.

[Official Npcap API](https://npcap.com/guide/npcap-api.html) documents `pcap_setmintocopy`: a larger threshold can reduce read syscalls but explicitly increases latency. Since this product models ~300ms one-way as test impairment and has strict ACK/Stop/low-latency requirements, do **not** adjust capture latency or buffer thresholds in this pass.

[Official Wintun API](https://github.com/WireGuard/wintun/blob/master/api/wintun.h) requires `WintunAllocateSendPacket` followed by `WintunSendPacket`; direct Rust M3 plaintext remains copied into the new Wintun TX loan for delivery. Not even the permissive trusted deployment context changes the driver memory ownership contract; optimize only the redundant NPF→Rust scratch copy. AEAD+PN verification and the already-good <=32 RX TX wake batch remain unchanged.

## Narrow code change and proof counters

- `crates/wbd-platform/src/windows_native_io.rs`: add `Captured<T>` enum and `NpcapRx::with_frame<T, F>(FnOnce(&[u8])->T)`. It calls the existing `next_ex`, preserves null/malformed caplen/len checks, constructs one borrowed slice and invokes callback synchronously. Callback returns **owned** `T`; no borrowed slice can escape the validity interval into later capture calls. Prior `NpcapRx::read` is retained for compatibility and existing tests/owners, not used by the native Windows RX hot path. This adds no C ABI fields, allocation, callbacks into Go or driver modifications.
- `crates/wbd-engine/src/v4_windows_native_runtime.rs::rx_loop`: remove the copied `frame=[0;MAX_NPF]` scratch, call `npf.with_frame` and inside the callback run original `ethernet_ipv4`, `parse_data_packet`, `open_and_deliver` with the existing trusted IPv4 tuple and M3/AEAD/PN owner. Keep existing 32-capture-bounded loop, thread worker Stop checks, AUTH/CONTROL semantics, only wake TX for verified ACK and preserve early handoff FIFO. Decode/auth/Wintun delivery must finish before next NPF read. No async spawn, no pointer retained.
- Count `NpfBorrowedStats{frames,bytes}` only on the single RX thread, no per-packet atomics/clock/log or allocations. At worker Drop (including graceful Stop) log one `WBD_WINDOWS_RUST_NATIVE_NPF_BORROW frames=... bytes=... extra_memcpy_bytes=0 lifetime=UNTIL_NEXT_PCAP_READ`; pure read-only CPU auditor captures the source-qualified marker if unique. This indicates **how many bytes no longer undergo the extra Rust scratch memcpy**, *not* kernel NPF packet-copy eliminated (kernel→libpcap transfer still happens).
- Windows unit tests exercise the actual Npcap callback mock, verify pointer equality (`frame.as_ptr()==IPV4.as_ptr()`), ensure callback does not run on invalid metadata, and all original copy/driver loan lifetime tests remain. Do not infer CPU speedup from unit tests.

## Production new-source qualification

Tag `[plan026-win-npf-borrow-150]` on main selects one Rust Normal/off V2 full 150Mbps **each direction**, 300ms one-way **each direction**, 0% injected real tc, 60s + drain, signed Npcap/Wintun+WSL2, original Go cold TLS and original kernel raw/TUN, both owned Stop. Product platform+engine source changed, so the workflow **MUST rebuild Windows original executable/Rust DLL and Linux peer** from the same new source; no SOURCE7fc old prebuilt reuse. CPU audit retains per-Rust-worker actual GetCurrentThreadId mapping to Win32 user/kernel CPU, and new caplen-borrow summary.

Strict PASS requires ≥142.5Mbps both offered, ≥99.9% first unique delivered both, real tc IFB/eth0 drops0 and Linux raw RX/UDP receiver socket drops0, Stop both PASS. Compare previous SOURCE7fc run40693430836 CPU total8.390625s/74.437s RX CPU6.42188s to new source only as **cross-VM indicative**; to claim causal CPU efficiency improvement run old/new on the **same Windows VM** with alternating order, qualified traffic and exact binary identity. If data plane or Stop fails, revert only zero-copy path, preserve previously qualified RX wake coalescing.

```feature-impact
{"kind":"updated","ids":["windows-native-transport","normal-off"],"reason":"Windows Rust NativeOwner authentic NPF RX now synchronously processes Npcap-owned pcap_next_ex frame bytes without an extra full-frame Rust memcpy, preserving M3/PN, Wintun driver-owned loan, Stop and <=32 TX wake batch. ABI unchanged; new-source real signed 150Mbps native qualification pending."}
```
