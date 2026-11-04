# PLAN028 H1118 — Windows native IPv4 event proof and next Linux ARM64 task

Windows [Action41803548026](https://github.com/lly8666/wbd-next/actions/runs/41803548026) SUCCESS, independently verified artifact13308298396 ZIP SHA256 `c2cfdfc7672e168f8c66862c165bbb9492ae284b2ad3278791f783a989d3d7ad`. A test-owned Hyper-V internal vEthernet (not the GitHub runner management NIC) was created, assigned private IPv4 source `198.18.246.1→198.18.246.9`, and destroyed at fixture end. Real native `NotifyUnicastIpAddressChange` callbacks =3; `NotifyRouteChange2` callbacks=1; `Find-NetRoute` OS selected source changed and read back. Windows briefly returned network unreachable while a new address came out of DAD; actual mutation→valid new selected route 3190.42ms includes OS address readiness, **not** a violation of the application's 200ms quiet/500ms notification coalescing, and certainly not a TLS/first packet time.

**Hard qualification boundary:** OS notification/native source selection only. No real Windows WBD original TLS, Npcap, Wintun, Rust/TUN, new session, packet, Stop or physical hardware NIC change was run here. This [evidence](../evidence/M0/PLAN028-H1118-WINDOWS-HYPERV-OWNED-NATIVE-IPV4-NOTIFICATION-20261104.json) is not a product PASS. Windows live Npcap source switch remains NOT_RUN until a test-owned real server exit and driver-bound packet proof are available.

Next whole-platform Linux task after H1116 x86/x86 must be native **ARM64 client + ARM64 server**; reuse SOURCE32cd compiled native ARM original Go/Rust ELF and the same real kernel two-Game4-group physical-switch fixture; no QEMU, no product rebuild, one Action one scene. Newly created Action is candidate until artifact verified. H998 historical same-connection MTU shrink FAIL, old ARM64 Game4 FEC Action FAIL, remote ICMP and CPU causality gaps unchanged.

```feature-impact
{"kind":"none","ids":[],"reason":"H1118 records independent native Windows OS-only environment receipt and adds a frozen ARM64 test workflow; product code unchanged."}
```
