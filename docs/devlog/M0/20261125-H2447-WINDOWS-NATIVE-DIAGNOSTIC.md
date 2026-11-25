# H2447 diagnostic
H2445 final Windows artifact15022859742 inspected. Server WAN rx delta39 packets/5583 bytes during failed session; Windows 958 tx_records, valid IPv4 rx0; no loss/RTT injected at failure. Normal TLS, READY and first generation WAL/Rust Stop confirmed; no forwarded TCP. Product delta 93b249e→5e1b683 limited to splice, queue, terminal HP, Wintun ring. Main product code identical to 93b249e. Use old/main original signed Windows functional test and current candidate exact H2441 same-source artifact original fixture, no H2441 wrong flag. Separately three runner NAT vs BBR, no injected loss/RTT, same current frozen artifacts, short TCP only, passive TCP header summaries at gateway eth0/h228bc and server WAN/TUN, selected actual active transport endpoint Windows route snapshots before/after Apply/Stop. Hypothesis only: access transport may be recaptured by Wintun full route after Apply; do not change route policy without evidence. No product changes, no performance matrix, no promotion.

```feature-impact
{"kind":"none","ids":[],"reason":"Controlled native regression diagnosis and passive observations only."}
```
