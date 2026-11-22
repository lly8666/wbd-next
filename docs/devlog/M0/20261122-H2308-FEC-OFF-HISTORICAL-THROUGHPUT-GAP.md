# M0/H2308 — FEC OFF 400ms 1/5% loss historically fast vs current Windows slow

Status: **HISTORICAL GAP VERIFIED; WIN BBR2 CAUSAL CONTROL RUNNING, NOT YET A FIX** (2026-11-22). Experiment-only, original Go TLS/Rust source locked; NO main or user OS global setting promotion.

## What the real source evidence says

| Run and source | FEC OFF+outer repair OFF original WBD product? | 400ms 1% Mbps | 400ms 5% Mbps | Congestion control / endpoint / topology |
|---|---|---:|---:|---|
| H2268 [44916507110](https://github.com/lly8666/wbd-next/actions/runs/44916507110), source 4c40061 | YES (A/A′), exact real kernel received bytes, both Stop | 76.889 / 75.193 | 30.427 / 37.006 | **Explicit Linux `tcp_congestion_control=bbr`** client+server, one native ARM runner **3 distinct Linux netns**, bidirectional 200ms iid kernel netem on router veth, physical MTU1200, product outer1160, `iperf3 -P 4 -t 20` |
| H2270 [44918335232](https://github.com/lly8666/wbd-next/actions/runs/44918335232), source b2743dd | YES (A/A′), zero actual native frozen retransmissions | 80.847 / 72.882 | 41.477 / 36.338 | **Same Linux BBR netns design**. B ON extra outer repair is distinct and worsens throughput at 5%; do NOT attribute OFF results to outer repair |
| H2228 [44705243325](https://github.com/lly8666/wbd-next/actions/runs/44705243325) | historical FEC OFF original WBD Linux product with then-enabled optional outer policy, so **NOT clean outer-repair-OFF comparator** | 1% product no valid session | 73.820 up / 23.069 down | Linux x86 original Go/Rust, ARM L3 VXLAN relay, Linux x86 server, native Linux BBR, different `gemodel` burst loss; no Windows or signed Wintun |
| H2280 [44928186966](https://github.com/lly8666/wbd-next/actions/runs/44928186966) | **NO WBD**, pure Windows Winsock→ARM kernel TCP; no Go TLS, Npcap/Rust, or Wintun | 3.491 / 3.178 | 0.789 / 1.001 | Actual dual independent Windows Server 2025→ARM relay→ARM server, 400ms bidirectional iid kernel netem. **But default 128KiB buffers limit 0% to ~7.7–8.0Mbps**, so this is qualitative only |
| H2307 [44988210204](https://github.com/lly8666/wbd-next/actions/runs/44988210204) 1% B_OFF | YES (B_off), original signed Win Npcap/Wintun → two-hop ARM relay → ARM real Go TLS/Rust TUN; exact 160 echo and real ARM byte receipt | **1.457 / 1.451** | separately H2306 5% has no complete bulk receipts at bounded 180s | Windows 2025 original kernel TCP, previously **no congestion provider selection or per-connection applied-setting readback**; relay Tailscale0 DNAT/SNAT instead of same-host native veth; test Python `sendall()` 4×25s then waits EOF and precise 8-byte receiver receipt |

All data come from committed source-locked files:
- [H2268 original run data](../../evidence/M0/PLAN029-H2268-ARM-LOSS1-LOSS5-200MS-ORIGINAL-OUTER-REPAIR-ON-NO-ACTUAL-R-20261121.json)
- [H2270 original run data](../../evidence/M0/PLAN029-H2270-LINUX-OUTER-ACK-SACK-RESTORE-REAL-LOSS1-LOSS5-20261121.json)
- [H2228 first true 3-runner matrix](../../evidence/M0/PLAN029-H2228-THREE-ARM-RELAY-GE200-REAL-TCP-20261120.json)
- [H2280 bare Windows kernel-TCP failure match](../../evidence/M0/PLAN029-H2280-REAL-WIN-ARM-DUAL-BIDIR-NETEM-20261122.json)

## Actual code comparisons

H2268 source 4c40061 to archived original ARM product 97db898: **only performance-relevant compiled change** is original Rust Linux `v4_embedded_go.rs` H2270 optional outer ACK/SACK feedback consumer, disabled when outer repair OFF (plus assembly manifest checksum change). The native original Go/Rust Linux FEC-OFF/outer-OFF TCP hot path did **not** have an identified 30→1Mbps source deletion.

H2268 to frozen original signed Windows TX16/Rust source dc2da4 additionally includes the opt-in H2291 Windows NPF send queue 8→16 and service batching, not proof of a high-loss TCP recovery bug. This is a **different operating system's kernel TCP sender**, plus WSL/Npcap/Wintun and two Tailnet UDP hops. Most of the apparent 1–80Mbps discrepancy **cannot** currently be labelled a product code regression.

H2268 app script `tools/m0_029_native_inbox_abca.py` explicitly runs `sysctl -q -w net.ipv4.tcp_congestion_control=bbr` inside both client/server netns, and uses `iperf3 -c ... -P 4 -t 20 -J` `end.sum_received`. H2306/7 original Windows signed native app uses four Winsock `sendall` flows then exact server-received-size receipt, **default Windows TCP congestion provider unknown prior to H2308 readback**. The difference between the Linux and Windows kernel congestion controllers is a **prime testable causal candidate**.

Windows 2025 official documentation supports `netsh interface tcp set supplemental template=Internet|Datacenter congestionprovider=bbr2`, `Get-NetTCPSetting` for effective profile parameters, and `Get-NetTCPConnection -RemotePort 45902` for **AppliedSetting** on the actual kernel-owned inner TCP streams. Because template selection may differ for tunnel/private addresses, **changing the intended template without readback of the active flows is NOT a valid experiment**.

## H2308 true product native BBR2 first tests, no FEC

- [1% original Windows→ARM 2x3Runner run 44989812209](https://github.com/lly8666/wbd-next/actions/runs/44989812209)
- [5% original Windows→ARM 2x3Runner run 44989812335](https://github.com/lly8666/wbd-next/actions/runs/44989812335)
- Exact source commit [cfcd116](https://github.com/lly8666/wbd-next/commit/cfcd1160ff646df0dd632b951132bb3ff4ac7e9c). Both conditions same original Windows Npcap/Wintun GoTLS/Rust and ARM original compiled binaries, FEC2 OFF, cosmetic outer repair OFF, 400ms/1% or 5% true dual kernel netem, **8→2→8MiB test socket buffers** (single profile within each A/B/A′). Four bulk real kernel TCP and 160 TCP echo, CPU/P99/Stop on genuine completion.
- Test-only `tools/m0_h2308_windows_cc.ps1` records actual Windows `Internet` and `Datacenter` original congestion providers **before modification** (timestamp-local ephemeral CI runner), attempts BBR2, demands real PowerShell BBR2 provider readback, and in a separate `if: always()` step restores both exact original values and compares actual restored state. The original OS outside runner and main not mutated.
- Test-only `m0_wl_loss_tcp_probe.py` samples **actual established Windows kernel TCP 45902 sockets** via `Get-NetTCPConnection`, and the Windows original business wrapper requires ≥4 active original 10.66.0.2→10.66.0.1 flows with applied Internet or Datacenter template; no success on intended but unproved template.
- A/B/A′ per profile source/binaries/P99 validation remains strict; a CC setup or route preflight failure is **INFRA/TEST**, never a Rust product 5% verdict. If 8MiB A succeeds but 2MiB B is slower or times out, preserve first-leg evidence rather than infer CC is ineffective.

## Decision gate

**Do not conflate Linux BBR 30–80Mbps with Windows 1Mbps until same topology + CC applied proof is examined.** If H2308 BBR2 significantly restores per-real-kernel-TCP FEC-OFF throughput, follow with same Windows-only CUBIC→BBR2→CUBIC and 400ms 0% negative control, P99 and CPU, then a narrowly scoped **opt-in** Windows lease transport profile (not a silent host-wide provider change). If BBR2 has no gain, inspect actual Windows provider selected, TCP window scaling/autotuning, Win→ARM packet sent-vs-received on TUN and relay, burst/drop and two-hop capacity; no random Rust queue expansion, no FakeTCP reliable retransmit, no main promotion. **400Mbps/5% remains NOT MET** until genuine user-facing complete product receiver goodput and P99 prove otherwise.
