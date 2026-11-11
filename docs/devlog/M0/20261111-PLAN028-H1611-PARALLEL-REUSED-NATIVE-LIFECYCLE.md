# PLAN028 H1611: Independent binary-reused Linux idle100 and dead106

User requests efficiency: reuse H1600 exact native source8a Go/TLS and Rust ISA-L binaries (three SHA reverified in each Action), and run separate 100s no-business Auto FEC native wake and 106s 100pct bidirectional kernel blackhole + new authenticated TLS/Rust real UDP as TWO independent GitHub Actions. Each Action one network test, separate Ubuntu VM; no Go/Cargo compile, no Windows/WSL/multi-Wintun, no skipped near-MTU.

Existing PLAN026 temporary fixture helpers are mature but their original server echo count/timeout source anchors changed. Only an ephemeral source-locked copy of the current same-binary native netns script restores those helper anchors (old helper rewrites echo target +1 and server idle timeout); actual original Go/Rust binaries and base fixture are unchanged, verified by zero product/fixture diff from SOURCE8a. The dead106 old helper historically exited before joining owner Stop; remove only that temporary premature exit to allow the base fixture's original exact client/server Stop to run. If result fails before business distinguish fixture/host from product. Real Health-dead both original peers and old PIDs remaining are required in the dead case. FEC Auto explicitly selected, product default still Off; Linux proof is not Windows idle/dead qualification.

Both Actions NOT_RUN until strict native result/artifacts return; do not repeat old 150s or near-MTU; all original failures preserved. PLAN028 IN_PROGRESS.

```feature-impact
{"kind":"none","reason":"Only source-locked ephemeral test-only reapplication of mature Linux idle/dead fixtures and two independent prebuilt actions, no product changes."}
```
