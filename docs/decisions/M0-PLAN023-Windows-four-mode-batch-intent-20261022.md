# PLAN023 Windows V4 remaining modes — batch intent

User requests completing Windows V4 Fixed, Auto, Game2, Game4 together and validating as one batch.

Current verified baseline: Linux all five public V4 modes source 111fd39bc9cfda3dc03ef10c80c43ff86ad07845 PASS in Actions 39629082813; Windows Normal/off scoped PASS 39629082860. Windows original Go V4 bridge and Rust owner implement only one lane and FEC off. Four modes require native Rust and Go data-plane integration, not only removing the capability check.

Acceptance: one source-locked Windows Actions build with original Go credential TLS, real authenticated Rust FEC2 Fixed/Auto, Game2/4 lane grouping, actual Wintun application packets, original WAL and Stop. A build-only or negative case is NOT a positive product PASS. Keep signed device identity and OS ownership checks; retain historical evidence.

M0 alone modifies main under registered epoch1; no old donor file may change. Work as one batch rather than per-mode release.
