# H2330 — direct Normal source into the existing Npcap sendqueue

H2326 complete Windows owner regression Action 45310696203 PASS (25 owner tests, two 66 platform suites), maximum regression 45310696193 PASS. H2327 source c828c45 independently frozen, 45310787767 in flight; do not modify or re-dispatch it.

Remove another full-frame copy on the default Normal ready batch. M1 knows exact frozen wire lengths after seal; prepare the existing Npcap-owned sendqueue as an exclusive loan, write each frozen record into its final frame slot, then finish the original IP/TCP/Ethernet header directly in the same queue after releasing the M1 lock. Submit through the original syscall/trace/short-prefix classifier extracted as one shared routine. No new queue, thread, wait, allocator per batch, PN/Seq or protocol change. Existing single-frame, queue-unavailable, batch-over-profile and Fixed paths retain their original ready-frame route; TX16/NPF8 still splits via original sender. Initialization of the original Npcap buffer happens once at cold attachment. No changed NPF limits. Exact wire/short-copy test covers mixed lengths, full copy, exact one-frame prefix and uncertain one-frame fragment, reuse. Native and real throughput NOT_RUN at commit. At the H2323 B observed rate this removes roughly another 31MB/s of full-frame copying plus overhead, not a measured speedup. Compare H2330 only against the frozen H2327 source after its result is read; do not roll back a proven gain without a counterexample.

```feature-impact
{"kind":"none","ids":[],"reason":"Internal native Normal first-send staging into the already existing Npcap queue; preserves current driver/profile, wire format and outcome semantics. No default performance qualification."}
```
