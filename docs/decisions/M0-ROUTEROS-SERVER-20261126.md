# M0 RouterOS server experiment — 2026-11-26

User authorized read/write and a separate RouterOS server branch based on experiment/m0-linux-tcp-splice. Branch experiment/m0-routeros-server, exact parent fbce0649b5557d48199b5c0206424afd2677c232 (H2477). Keep main, parent branch, its active H2477 and role cursor untouched; this is a side experiment, not a replacement for the active M0 work. No production code change in the initial step.

Use quickchr 0.7.0 (https://github.com/tikoci/quickchr), Bun 1.4.4, CHR x86 7.24.7 long-term; QEMU KVM if available, TCG otherwise. Build original x86 product once via existing glibc2.31 assembler, same manifest across three isolated VM jobs. Local image archive transfer, real RouterOS container, host native Linux client and independent origin L2 segment. No SLIRP data-plane proxy. CHR free license is not a throughput qualification.

- Routed: client 10.248.81.3 -> CHR ether2 10.248.81.2 -> br-wbd 10.248.82.1 -> container 10.248.82.2:443. Origin is 198.18.77.2 via ether3 198.18.77.1. Exact forward rules for both directions; no additional RouterOS source NAT needed in this isolated routed lab.
- DNAT: same topology, client instead connects to CHR ether2 address:443, normal RouterOS dstnat to container:443. Separate VM, same product and origin, no other transport change. Determine whether the original carrier survives translation.
- Splice: same routed topology, explicit cubic kernel CC; test existing transparent TCP path, not new TCP implementation. BBR availability recorded but not assumed.
- Container entry probes actual TUN, forwarding, iptables MASQUERADE, TPROXY, fq. If fq unavailable use existing explicit 0, label it; no claim of matching default performance. Scoped RST suppression matches existing Linux lab. No new steady state safety framework, no changes to TLS/auth/wire/recovery.
- Success requires real authenticated client READY, existing H2429 finite bidirectional TCP/half-close + eight concurrent streams + UDP echo, owned client/server Stop, and actual splice target/Stop in splice scene. Archive source manifest, checksums, RouterOS readback/filter/NAT counters, container/client logs, bounded wire header sample and application receipt. NOT_RUN until Actions evidence. No physical router deployment, no throughput claims.

Main registry/cursor intentionally not overwritten while prior M0 work is active. Use this decision and branch commits as side-experiment handoff.

## Fixture correction before first results

CHR free is limited to 1 Mbps upload per interface (MikroTik CHR licensing manual). The first dispatched 5c6006b workflow uses original H2429 2/3 MiB and eight parallel 1 MiB downloads; its 35 s worker join may exceed license capacity. Keep that original run as evidence, not an unconditional functionality rejection. The corrected branch uses the same application logic at 1/16 payload (128/192 KiB, eight 16/64 KiB flows, unchanged UDP), records license, and retains exact bytes/hash, half-close and Stop requirements. No runtime or protocol change. This is a new source-locked functional fixture, not a throughput benchmark.
