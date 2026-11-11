# PLAN028 M0 H1609: Parallel prebuilt native Linux path receipts (2026-11-11)

Test harness SOURCE 196d3420244998323b8708f1ca63338763707cda; product Go/Rust executable SOURCE 8a31375e36bb6a93860c5579e64b4a39d0b6e346 (same unchanged product source, no new build).

Two independent GitHub Actions and Ubuntu x86_64 VMs ran concurrently, exactly one real native network scene each; both have overall and native job SUCCESS. Go pinned original TLS and Rust ISA-L native engine binaries were directly restored from successful H1600 Action 43027983611, three ELF hashes, native acceleration feature and Go source verified; product and native fixture Git diff from frozen source empty. No compiler step.

- Normal Off + Auto: Action 43046531699, artifact 13866924204 (ZIP SHA256 2899cdea221be37b2669cf3cb03869ee0554575b810cf4c3d4b6ec1c38e8615f). Original kernel source IPv4 10.25.0.2 to .3, physical MTU 1280 and derived TUN MTU 1209; protected real lease 10.66.0.153, 5 first + 5 after-switch actual OS UDP echoes, new original Go TLS/Rust M4 ready before old exact Stop, shared Rust single reader joined, routed10 unrouted0 backpressure0; original OS native Stop passed.
- Game4 + explicit fixed6 + Auto: Action 43046531950, artifact 13866424747 (ZIP SHA256 c14ba91a95d1d6bba3ece7725230452ce409b0a4f597d2e3003fc5e24679229e). Actual source4 .2 to .3, physical MTU1280 and TUN MTU1178; 8 genuine original Go/FakeTCP TLS443 ClientHello, 4 lanes each old/new cohort and eight distinct session IDs, zero early private server bytes, native authenticated Rust M4 generation2 before old A Stop; true FEC parity on both generations, single shared TUN reader and 5+5 native OS UDP echoes; Game4 owned Stop passed. RX stage count 10775 below 100000 spin bound; not a CPU improvement claim.

Native log SHA256: Normal 3685540f45ad0356ccbf449429f8b7b9fdd50a5b945cd80bf13686fe62ea5a89; Game4 fec47e58e61578e1d1d1da9f9df8510b0bcc2f44a5078a654b70f164b216e639. Original independent ZIPs and exact parsed evidence in docs/evidence/M0/PLAN028-H1609-SOURCE196D-PARALLEL-PREBUILT-NORMAL-GAME4-PATH-20261111.json.

Do not claim Windows Wintun/path, near-inner-MTU UDP, new 30m L3, 250ms/30% loss or CPU p99 from these short Linux scenes. User explicitly skips the previous H1602 nearMTU test and multiple Wintuns; prior environmental FAIL still retained. PLAN028 IN_PROGRESS.

```feature-impact
{"kind":"updated","ids":["linux-raw-tun","path-mtu-budget"],"reason":"Attach original source-locked independent Linux Normal and Game4 prebuilt authenticated physical path switch, TLS, FEC and owned Stop receipts; no product source, defaults or protocol changes."}
```
