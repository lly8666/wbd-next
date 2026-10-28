# M0 PLAN026 Rust real 150Mbps high loss — native Linux raw socket attribution

**Current unchanged Rust binaries:** compiled source `0543b805ca25d804ccd131be6686b0b99f61f80f` from run 40668581343. **New Python-only harness:** SOURCE `4e3db33805c375372f9187449eeb05333de8f0e1`, run [40673750173](https://github.com/lly8666/wbd-next/actions/runs/40673750173), artifact 12808369702 SHA256 `482b033ccce98924d5d8fad5f10b84c2f374cdb88e810edae55f00229a709f5e`.

Windows→Linux real offered 149.9599Mbps/1234860 packets, Linux app received 135.4067Mbps/1116215 packets, 118645 missing (9.608%). Linux→Windows offered 146.1655Mbps/1203614 packets, Windows received 144.7718Mbps/1192026 packets, 11588 missing (~0.963%). Genuine TUN/Npcap and both owned Stop pass. Both kernel tc netem qdisc drops zero. Linux Python consumer CPU61.1531s of 65s, max loop pause139.824ms; Windows Python sender CPU37.5625s, max loop pause16ms, continuous 10ms send hist. Linux losses in 300/302 seq windows, not the previous one-off t5 500ms pause. Neither Linux high Python CPU nor Rust AEAD alone explains loss.

**Independent decisive Linux raw stage:** original server.log `V4_PUBLIC_RX_CHAIN raw_observed=1132269 ... data_unique=1118872 ... tun_delivered=1118872 ... tun_udp=1118858 tun_failed=0 open_invalid=0`. Linux UDP app first received1116215, only 2643 below kernel TUN UDP output. Windows native TX 1236096 copies, Linux IFB inbound netem1250530 packets (control and session scope differ, no exact conservation), netem drops0. The bulk gap occurs before Linux original Rust raw observer, or at its kernel receive socket. Linux Rust `linux_raw_carrier.rs` opens `SOCK_RAW IPPROTO_TCP` without setting receive buffer; this is a bounded hypothesis, not established failure root.

**Next opt-in fixture-only observation:** read Linux guest `/proc/net/raw` per-inode raw socket queue/drops and `/proc/net/udp` independent generator socket inode/drop, plus actual `SO_RCVBUF`, `rmem_max`, UDP MIB RcvbufErrors. Start/1Hz/end only, not per-packet instrumentation; do not tag unknown as zero or silently alter host sysctl. If raw drops large (~1e5), review actual kernel socket capacity vs sustained PPS and add strictly scoped Rust receive buffer sizing with readback/caps; if zero, isolate Windows→WSL2 underlay to Linux IP/raw handoff and verify per-stage counts with common window. No old-Go A/B effort and no changes to Rust protocol in this commit.

**Efficiency proven:** fast native job217s+cheap gate12s, previous full native340s + Linux build100s + parallel compilation up to135s. Precompiled SOURCE and SHA checked, Npcap/Wintun true signed installed, WSL2 genuine, no Windows/Linux new binary build.

```feature-impact
{"kind":"none","ids":[],"reason":"Additional read-only Linux /proc raw and UDP socket drop snapshots in genuine independent Rust-only traffic generator and its unit tests; source-verified prebuilt product remains unchanged, no Rust product hotpath/wire/Stop changes."}
```
