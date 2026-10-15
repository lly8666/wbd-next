# M0 strict inbound TCP parse before authenticated record — 2026-10-15

## Recovery and four worker acceptances
M0 original kernel batch SOURCE17bb909a scoped native21/21 platform +2/2 fullpacket SUCCESS. Its originally blocked evidence write was replaced by recovered evidence S f20e110e and cursor-only H16347c64 sequence45; both Governance checks SUCCESS 38668360180/38668430534. No old source was rewritten.

Audited each commit since previously checkpointed Worker branches and each cursor-only H and exact Actions:
- M1 ready-only batch SOURCE3460d4f, native39/39 run38667033577, H4ca7d283 Gov38667280279 SUCCESS; historic branch R0 ABI marker-count Actions38667033555 FAIL despite Rust42/42.
- M2 global grant batch SOURCEe77e0de, native28/28 run38667347598, H7043ad19 Gov38667689189 SUCCESS; previous fake-clock fixture failure and code SOURCE governance main-moving FAIL recorded.
- M3 FEC retire-pressure SOURCEe8d62776, native75/75 run38667240535 and 7/7 worker scoped Actions SUCCESS, H6fe26165 Gov38667890659 SUCCESS. Genuine late timer bug fixed on worker, not yet imported to main.
- M4 strict incoming IPv4/TCP SOURCEdd5a7dc7, native31/31 run38667179420, H48d8e270 Gov38667553300 SUCCESS; old root R0 expected-count test Gate FAIL remains.

Assigned next independent scoped atoms on existing registry revision2 epoch1 without changing worker branches/owned paths: M1 R1-M1-RX-READY-BATCH-005, M2 R2-M2-BATCH-EPOCH-RECEIPT-RACE-004, M3 R1-M3-AUTH-FEC-SCOPE-GATE-011 and M4 R1-M4-LINUX-RX-BATCH-005. Exact registry SOURCE06601c0, decision SOURCE1d58c0; main-only decision document must NOT be referenced in worker branch cursor unless it exists locally.

## M0 CODE SOURCE and exact actual Actions
CODE SOURCE **d80bc75073b07be965e9f78ef5c029b06fe91c73** imports M4 strict RX byte-only `rx_ipv4_tcp.rs` and module registration. Main test extends true Linux x86_64 GNU kernel sendmmsg unprivileged UDP: M1 frozen → M3 AEAD seal → M4 full TCP writer → actual kernel send → bounded strict parser returns UNAUTHENTICATED ciphertext, then M3 AEAD and PN replay gates business. It confirms TCP seq32 extension only against caller-trusted anchor; an attacker can repair TCP checksum after tampering with ciphertext but **cannot** pass AEAD or advance replay, and subsequent valid first business does not HOL wait. Outbound packet fixture still copies bytes into an Arc, no OS raw RX device, no Go V4 exporter, no product.

Exact same CODE SOURCE **12/12 triggered Actions SUCCESS**. Native [IPv4/TCP Actions38668693087](https://github.com/lly8666/wbd-next/actions/runs/38668693087) 31/31 platform; actual Linux [kernel Actions38668693097](https://github.com/lly8666/wbd-next/actions/runs/38668693097) platform31/31 + M0 strict parsed+AEAD full packet3/3; both compiled once and checked by separate consumer. Other successful same SOURCE: R0 native ABI38668692785, R0 cross ABI38668692957 **compile/inspect only**, R0 fake platform38668692970, R0 static38668692936, governance38668692985, R1 wake38668692963/normal38668692974/FEC38668692922, R2-auth38668692811, G2 38668692736.

## Scope and next M0 action
Design READY, repository phase R0_FOUNDATION_IN_PROGRESS and product/physical NOT_RUN. Kernel UDP fixture demonstrates true syscall and exact records, not AF_PACKET raw-TCP carrier. Go V4 trusted session identity/generation export, Linux raw RX and Windows native, full owner lifecycle, multi-lane, 500Mbps sustained p99 and physical measurements remain pending. M0 next code atom independently imports M3 tested late FEC Heavy timer retirement fix with its own codec tests; longer critical path binding authenticated Go V4 cold state to steady Rust per-direction scopes. Four workers now have distinct new atoms, but assignment is not automatic execution.
