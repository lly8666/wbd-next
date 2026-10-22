# PLAN024 S778 — parallel Windows M2 authentication and real Npcap/WSL ingress (2026-10-22)

Resume M0 active rev3 epoch1 main from H247, HEAD `e5cb79551e9a6fae79500dee3af7b83a7930e9ec`; prior Governance `39728944122/1` SUCCESS. Preserve S776 exact environment PASS SOURCE `64e8560ec3e9161c4e8976a27118cc1e1935f766` Action `39728479563/1`; original S774 `39728097436/1` FAIL recorded, no edits to historical results. User requests parallel acceleration, NOT global mode promotion or worker reassignment.

Independently prepared lanes with separate source paths, but serialized main commits to respect M0 writer and cursor:
1. Windows Rust owner recovery ingress: original Go TLS-scoped Rust M1/M3 opener must pass AEAD+unique PN-authenticated kind1 to M2 on the SAME session, never raw TCP ACK. Reuse Linux receipt codec/M2 state and bind exact epoch, lane and reverse-direction. No copied/mock cryptor. Test malformed/replay/stale/Stop and source-locked Windows native C ABI; do not widen capability bits to simulate pass.
2. Real native driver: pinned old Npcap service already signed PASS; run original Windows Npcap physical vEthernet native capture/send across actual WSL2 Linux AF_PACKET on a runner, ensure same packet bytes/ethernet tuple and service cleanup. Only succeeds with actual kernel frame receipt; if platform isolates vSwitch/adapter report BLOCKED rather than simulating traffic.
3. Source-locked protocol/peer: remove private Go 256 unACK/750ms×8 retry only after authentic Rust M2 frozen shadow/feedback/timer and first-send kernel outcomes are wired; do not merely raise static backlog limit, forge ACK, or disable retries.

Parallel work comprises independent investigation/test preparation; main commits are sequential, tests have exact independent SOURCE and Action. Public original TLS→Rust Windows→Linux business, owned Stop, WL-N0/N1/N5 each 10Mbps 60s remain NOT_RUN until proven.
