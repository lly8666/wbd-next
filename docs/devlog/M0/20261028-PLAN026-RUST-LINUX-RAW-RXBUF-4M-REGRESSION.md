# PLAN026: Rust-only Linux raw socket RX overrun bounded fix with 100Mbps regression

## Recovered, measured hard facts

Historical FEC branch `experiment/fec-network-tuning` owned Linux TUN **fq600 is already in main**: `r0/go_overlay/internal/v4productcli/linux.go` applies `tc fq maxrate 600mbit flow_limit 256`. Real Windows→WSL2 at 100Mbps Action [40677430821](https://github.com/lly8666/wbd-next/actions/runs/40677430821) confirmed exact `V4_PUBLIC_TUN_FQ ... readback=kernel_fq_600Mbit`; despite that Linux raw socket inode 9367 `/proc/net/raw` dropped **1800** and app lost **1779** unique UDP packets in 60s (99.7839% business receipt), Linux UDP app socket drops **0**, netem qdisc drops **0**. Reverse Linux→Windows 100Mbps **zero app missing**. Both owned Stop PASS.

Same compiled source `0543b805ca25d804ccd131be6686b0b99f61f80f` in a separate hosted VM Action [40675314979](https://github.com/lly8666/wbd-next/actions/runs/40675314979) at 150Mbps each direction dropped **162785** at Linux raw RX socket; Windows→Linux app lost 175620. WSL2 `net.core.rmem_default=212992`, `rmem_max=4194304` bytes. Raw OS receive socket was created as `AF_INET/SOCK_RAW/IPPROTO_TCP` with `SO_BINDTODEVICE` and exact BPF after admission, **no SO_RCVBUF request**. Guest socket inode is not yet PID-attributed in archived 100Mbps runs, so a new *one-shot* read-only `/proc/<pid>/fd` exact-inode join will be saved with the next run. At high load each 60s sampled second of 150Mbps increased raw drop counters. Windows product/TUN/AEAD/M2 not demonstrated responsible.

Old Linux success **500Mbps** Action [40056105730](https://github.com/lly8666/wbd-next/actions/runs/40056105730) was one **TCP** stream, on Linux ARM64 native veth, fq600 source-TUN pacing, 0% netem, 200ms one-way, 60s: zero missing. It does not test a 100/150Mbps **UDP** source at WSL2 raw RX. FEC W23 150Mbps/dir 30% IID had residual ~0.75%; W168 250Mbps/dir ARM64 residual ~0.01–0.02% but x86 failed. FEC RX640/48MiB buffers are *post-authentication RS decoder* not Linux kernel socket RX.

## Narrow current code change and deliberately large but bounded margin

`crates/wbd-platform/src/linux_raw_carrier.rs::ScopedRawIpv4Rx::open`: immediately after validating and binding only its owned raw IPPROTO_TCP fd, request `SO_RCVBUF = 4 * 1024 * 1024` B (4 MiB). Linux doubles the accepted request to account for memory metadata; the effective value is up to **8 MiB per owned RX socket**, a conservative ~20x increase over original 212992B guest default. Do not use `SO_RCVBUFFORCE`, change any guest/host sysctl, arbitrary app socket, FEC code pool, network tc/fq, sender pacing, MTU, game modes or Stop owner. Read exact `getsockopt(SO_RCVBUF)` and log actual (including `kernel_capped=true` if below8MiB). If setsockopt/getsockopt fails or reports invalid/out-of-bound value, drop owned FD and fail closed; do not continue unfiltered or without verified owner. A 4MiB kernel `rmem_max` SHOULD allow effective 8MiB but actual kernel readback is the only proof. Memory growth is bounded by RX socket count and kernel caps; no upfront Rust allocation.

Add Linux unprivileged temporary UDP socket test for SOL_SOCKET ABI/readback/bounded effective maximum, not a mock raw driver. Fixture Linux userspace reads `/proc/<pid>/comm` + `/proc/<pid>/fd` symlinks for the **exact wbd-v4-server/client binary basename** and intersects with `/proc/net/raw` inode just once at the end, returning actual PID, inode and role. Reject false attribution to unrelated processes. Every 1s cheap socket drop/count queue polling unchanged and never per packet.

## New source regression contract

Tag `[plan026-rust-rxbuf-100]` selects **100Mbps each direction**, 300ms each direction one-way, 0% configured kernel netem loss, 60s and same 96/288/1060/1200B weighted UDP packet mix/seed as Action40677430821. Unlike harness-only prebuilt previous runs, this product change under `crates/` MUST execute new Linux Rust+Go original TLS native build and Windows Rust DLL/source compile and SHA manifests of **same new commit**. Wintun/Npcap signed real drivers and original WSL2, TCP/UDP functional, immutable owned Stop unchanged. No legacy steady Go A/B.

Pass only with compiler/tests **and** actual dual-direction offered>=95Mbps, first unique business receipt>=99.9% each direction, real `tc netem drops=0`, Linux exact product raw RX socket drops=0 (or explicitly disclose if residual), actual readback effective bytes, source/version/manifest matching, Stop both. Any incomplete real Action remains NOT_VERIFIED, never claim fixed from a code change or test build.

After qualifying the 100Mbps regression, isolate 150Mbps with same new binary in separate source-locked V2 scenario; do not repeat entire A/B or infer matched VM CPU improvement. If drops persist despite real >=4MiB effective buffer, investigate raw packet consumption cadence (`poll(0)`/batch), guest virtio queues, WSL/HyperV vNIC and compare stage-level counters before changing more buffer budgets.

```feature-impact
{"kind":"updated","ids":["linux-raw-tun"],"reason":"Linux Rust real raw IPPROTO_TCP RX owned socket receives bounded 4MiB SO_RCVBUF request (<=8MiB Linux effective readback) to address authentic kernel raw socket drops; preserves existing fq600, TCP/UDP protocol, FEC, owners and Stop. Exact Windows+WSL2 performance qualification pending new source."}
```
