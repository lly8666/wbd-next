# W24 native ISA-L coefficient-table reuse candidate (2026-10-24)

**Owner/branch:** fec-network-work on experiment/fec-network-tuning.
**Prior pinned product:** 6b08527dbb0af8a626760ff83abcd06de1d42d87,
ARM64 build Action 40099179830 artifact 12562092730 SHA256
e3509e34a11f4763011c08312d02270e560ac7d04f5136ad22f76b5990f4cda5.
W23 Action 40102994265 artifact 12563149315 SHA256
f64b606746b3a7b317e81fb5fb8849447ceed1cc21607624508743567c01f9c4.

## Computation and causal limit

At 150Mbps/side 30% IID/300ms Maximum6, accepted first-source
663652/663656 over 45s, full blocks40953/40953; 20 parity rows per
full block => five 4-row native ISA-L table initializations **per block**
on the old source. This is approximately 4550 repeated initialization
events/sec/side before accounting partial blocks. Source-side M4-copy
failures0, RX pressure0, TUN drops0, outer DATA retrans0.
W23 rplanned 830246/830265 and r_sent800359/799115, gap3.60/3.75%;
unknown_capacity2983/3054 BUT pressure_jobs0 and source_pressure0;
parity seal failure48/63; queued expired335/347. Code inspection shows
unknown_capacity also increments on in-flight job expiration; no
thread-level or codec causal benchmark yet. FixedStream Maximum closes a
job after 10ms and needs 5 M4-settled 4-row quanta. This proposal does
NOT increase the timeout or weaken source-first priority.

## Change, bounds, qualification

Reuse ISA-L Tables immutably keyed only by k, absolute row start and
row count, with a fixed 16*20*4 lazy slot set. All valid native k>=2
shapes together have at most 777600B native coefficient table payload
plus bounded slot and allocator metadata. Source payloads, PNs,
generation, sealed rows, M4 outcome, FEC parity volume and other outer
repair paths are unchanged. Scalar/non-native remains exactly as-is.
Add native cross-block different-sources complete 20-row oracle and
explicit ARM64 test in existing product-build Action. Build correctness
first; then W24 single 150Mbps 30%IID 300ms one-VM AB with A=old frozen
binary and B=new precise SOURCE, two 15s warmup+30s measurement periods,
independent cleanup and per-leg readbacks. No 175+ pressure until parity
gap and CPU pressure support it. Strict performance result NOT_RUN until
that Action finishes; no performance gain claimed from compilation.

Auto dynamic full profile transitions and truthful RTT age remain
independently OPEN; original network-matrix branch/status untouched.
