# M0 recovered native Linux kernel batch handoff · 2026-10-15

Recovered by M0 from the remote CODE SOURCE `17bb909aad62f4bd3d7b68f427feb9e88e429e01` and the existing GitHub Actions; prior attempt to publish evidence did not update remote main. This is **not** a new code build.

M4 worker SOURCE `6e72152f616e9bc836e3b66cd8742915abf6b5b3` independently qualified 21/21 Rust native Linux x64 GNU sendmmsg tests in Actions 38598122174, worker H `47eb4107` Governance 38598800683 SUCCESS. M0 imported the FFI, guard and authored in-process integration: M1 frozen owned buffer → M3 sealed record and post-receive PN anti-replay → M4 complete IPv4/TCP with independent checksums → real kernel sendmmsg on connected UDP loopback → exact byte replay.

First main code `dac23cdb` had r1-ipv4-tcp-native run 38667156675 FAIL because the old workflow asserted 12 while actual Rust r1 tests 21/21 PASS. Intermediate `93a2ac32` fixed exact count; final CODE SOURCE `17bb909aad62f4bd3d7b68f427feb9e88e429e01` checked both source-triggered workflows jointly. Exact Actions governance 38667409709 SUCCESS, IPv4/TCP 38667409612 21/21 SUCCESS, native kernel 38667409653 platform 21/21 and M0 kernel packet integration 2/2 SUCCESS. Binary, artifact SHA hashes and limits in `docs/evidence/M0/R1-M4-kernel-batch-main-integration.json`.

**Scope**: actual Linux x86_64 GNU sendmmsg kernel syscall using *UDP socket fixture*, not AF_PACKET raw TCP. M0 outer packet Arc is a test copy; kernel accepted is not peer receipt. No live Go V4 session/extractor/epoch, Windows native, performance, physical or product qualification.

Next: audit newly completed M1 39/39, M2 28/28, M3 75/75, M4 31/31 own worker branches, verify per-commit paths and cursor-only H Governance; then issue independent next atoms under unchanged role ownership and progress M0 trusted authenticated RX handoff.
