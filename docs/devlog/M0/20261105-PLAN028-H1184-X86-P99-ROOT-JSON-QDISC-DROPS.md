# PLAN028 H1184 — native 5% Game4 200 UDP RTT 20.013ms real, fix evidence JSON ownership

[H1182 x86 native Action41893407117](https://github.com/lly8666/wbd-next/actions/runs/41893407117), SOURCE7db artifact13355007767 zip SHA256 42137fb6e77e96a66485fbdfb38f1f0838f0043303cbc7bbfc4a11069c3a40bf. Original Go TLS/Rust Game4FEC6 on one443 completed actual two physical source4+MTU handovers, new generation3 Ready, exact generation2 Stop. Real `tc netem loss 5%` on Bob's physical mxb0 reported **2365 sent / 101 dropped** kernel packets; true protected inner UDP 200 sent **200 received**, received-only RTT p99 **20.013ms**, max arrival gap **20.003ms**. Original OS qdisc readback after removal was `qdisc noqueue`. Nevertheless Action FAIL: Python RTT stage ran as root within network namespace and created root-owned `plan028-h1178-game4-netem5-rtt.json`; final unprivileged runner Python could not append the genuine qdisc restored receipt, raising `PermissionError`. This prevented long Normal320/owned Stop from completing, so do NOT promote full PASS.

H1184 test-only exact fix: `sudo chown` the single already-created JSON to runner ownership before final Python update; independently parse actual `tc -s` output and require positive physical drops, write verified `physical_qdisc_dropped_packets`, keep real UDP p99 and native cleanup gates. No chmod world-write, no new wire/FEC/AEAD/PN, no Health90 change. One new x86 original-source Action. H1183 signed Windows independent one-mode Game4 still in-flight. Historical H998 old hot MTU-shrink and ARM Game4 Action FAIL, remote ICMP/Android and CPU causal gaps retained.

```feature-impact
{"kind":"none","ids":[],"reason":"Test artifact owner handoff plus require true kernel qdisc dropped packets, no runtime or feature change."}
```
