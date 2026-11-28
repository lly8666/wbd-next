# H2530 candidate — independent native feedback comparisons

H2528 frozen db76055 120/600M load test accepted H2529: 107.72/301.57 Mbps, retired retrans 0.00208%/3.32145%; low-load sampled gaps zero including one 64MiB receive buffer, high-load cross-runner gaps. The path is not proven physically loss-free. Do not repeat fixed ceilings, quantum8, gentle Startup, ACK grant, ready drain, buffer enlargement, fast retrans clock or receive-growth deletion.

Compare mature Linux tcp_bbr.c (bbr_packets_in_net_at_edt, bbr_set_cwnd) and tcp_output.c pacing against current separate reservation/admission. Two independent narrow candidates in the existing paired Middle BBR1; no outer change, fixed rate, window limit, new controller, new queue, timer, thread, or cross-flow HOL.

- B (admitted): ACK-before BBR1 already observes admitted_pipe while ack_info post-ACK uses reservation-inclusive in_flight. Feed actual admitted post-ACK pipe to BBR1 in this arm; generation still charges reservations against cwnd/native grant. The discrepancy is at most current pending reservations, not evidence it explains all loss. Unit checks reservation and admission transitions.
- C (service): existing credit can accrue during the local reservation-to-M4 wait and immediately release another grant when native pending drains. Rebase the existing pacing accrual timestamp at the actual final native admission, preserving already earned positive credit/debt, the existing rate and quantum. No new scheduling clock or hard rate limit; the possibility of underutilization is a testable risk. Unit checks stamp, rate and credit.

One experimental per-flow selector, read only on paired Middle BBR1 construction, default baseline. Existing periodic TCP_INFO records selector and native reserved bytes; no per-packet log or new hot-path monitoring. Same candidate binary all arms A/B/C/C/B/A, server-side intervention only in recovery tests. Two extra native functional profiles (both endpoints enabled) on x86_64 and ARM64, preserving actual bidirectional data, eight concurrent connections, UDP and Stop. ARM clean/pause and 0.5% weak mirrored arms on same binary; 96MiB/120M/400ms. Three distinct ARM runners mirror A/B/C/C/B/A at 1GiB/600M/400ms/zero injection, existing Normal/repair/MTU1160/eight taps and bare brackets; all manifests from exact same SOURCE qualified dual ISA run. Compare actual throughput, CPU/GiB, first arrival, retired inner retrans and path/admission. Weak and multi-flow are required; no promotion from screen alone. B/C are hypotheses, not proven fixes. Remove rejected selectors on closeout. L2 remains open.

References: https://codebrowser.dev/linux/linux/net/ipv4/tcp_bbr.c.html ; https://codebrowser.dev/linux/linux/net/ipv4/tcp_output.c.html . Existing evidence: docs/evidence/M0/20261128-L2-FROZEN-CARRIER-LOAD-RESULT.json .

```feature-impact
{"kind":"updated","ids":["dual-rust-tcp"],"reason":"Screen independent admitted-pipe and service-epoch feedback candidates with one qualified artifact and mirrored workload; no product promotion."}
```
