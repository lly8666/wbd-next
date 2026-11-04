# PLAN028 H1205 — native ARM Game4 highest real tc30%/250ms PASS

[Action41933405513](https://github.com/lly8666/wbd-next/actions/runs/41933405513), SOURCE `abbaebe75e10605510dc7a284ebeaccc6a586a1d`, native ARM64 client+server original Go TLS/Rust one443, artifact13371649337 SHA fb10a58fee7cab6a0b32e62b6ad6130f648861de5de15288f924e67661233114 full PASS. Real mxb0 physical DOWN 1321.22ms before new protected Game4 gen2 M4 TLS READY (command→ready1595.6ms, NOT notifier→TLS/first packet), user outer1460, OS inner Game4 1178 and independent Normal1375. Only AFTER authentication, physically applied kernel `tc qdisc netem loss 30% delay 250ms`, actual 1708 physical packets /736 dropped; 200 inner UDP 10ms paced without application retry, actual 200/200 inner replies and received-only RTT p99 **270.013ms**, max adjacent arrival gap20.003ms, unaffected separate Normal16 native UDP. Real qdisc removal/readback and final original Rust TUN Stop PASS. Do NOT infer zero physical loss or high-loss during original ARM TLS; 30% setpoint is distinct from cumulative kernel drop fraction. H998 historical same-connection hot shrink and ARM Action FAIL retained.

The other 30%/250ms representative Normal highest fixed6 **during** second physical TLS on x86 is separately in-flight Action41933848259. Original Linux 7 mode-specific A-B-A scope qualified, but Windows 7 physical switches, precise event→TLS/auth→first, CPU causal, remote ICMP and Android still NOT_RUN.

```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient"],"reason":"Promote one ARM native original Game4FEC6 genuine postauth 30%/250ms kernel packet drops and received-only UDP RTT p99/Stop as strictly scoped PASS."}
```
