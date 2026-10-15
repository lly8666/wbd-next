# M0 R1-M0-M4-LINUX-RX-BATCH-MAIN-011 · 2026-10-15

## Authority
M0 start main H `2e3912ff7a4aed59400356598ae54cd7045bae30` cursor sequence47, checkpoint `a2e411e03b03e3aa642b955370c7db689e3a0d6a`, Governance38670384584 SUCCESS. Main registry rev2 epoch1 worker scopes unchanged. Four worker branches advanced independently; for each audited exact code→evidence→cursor H ownership and confirmed H Governance, without modifying worker branches.

## Worker acceptance (SCOPED, not product)
| Role | Worker code SOURCE | Native compiled-once | H Governance | Main integration status |
| --- | --- | --- | --- | --- |
| M1 RX ready batch | `e0a9f64d5c17d8085c52f09a083b9689535f00d1` | [38669368706](https://github.com/lly8666/wbd-next/actions/runs/38669368706) **51/51** | H `fa518d65`, 38669632237 SUCCESS | accepted and queued; not imported |
| M2 epoch ACK/repair race | `06fe27ae516cdef6b144c736a2166a5f6d4b209f` | [38669519161](https://github.com/lly8666/wbd-next/actions/runs/38669519161) **33/33** | H `43c0e985`, 38669865546 SUCCESS | accepted and queued; not imported |
| M3 authenticated FEC scope | `42382c60ee51689d49c480411af3df2acc9e9a7d` | [38669822925](https://github.com/lly8666/wbd-next/actions/runs/38669822925) **85/85** | H `f56a6720`, 38670975617 SUCCESS | accepted and queued; positive origin constructor cfg(test) only |
| M4 Linux RX recvmmsg | `2a4bc0e856f84042da292a4fae93d2a32d2d10db` | [38669449668](https://github.com/lly8666/wbd-next/actions/runs/38669449668) **42/42** | H `7bbd60d1`, 38669770858 SUCCESS | integrated this atom |

Worker historical failures not laundered: M1 R0-native-ABI workflow38669368889 unfiltered count FAIL though 54 Rust tests passed; M2 first SOURCE15b696f9 native38669397068 fake MonoNs order 32/33 FAIL corrected at SOURCE06fe27ae; M3 source governance38669822950 attempts1–4 main moved/role-scope race but attempt5 PASS; M4 old R0 fake platform38669449646 count gate FAIL while isolated native42/42 PASS. These do not alter role-owned source test acceptance or establish product PASS.

## M0 code SOURCE and tests
M0 imported M4 `linux_rx_batch.rs` verbatim from qualified SOURCE and registered it in platform under its own Linux GNU x64 unsafe island. Added two M0 integrated native tests and updated two native Actions exact selectors/count 31→**42** platform, main integrated 3→**5**. Exact code SOURCE `f5dcb230804531c7dd558d3ef624f99faeca25d6`.

Native Linux x64 GNU fixture: M1 genuine frozen records → M3 real AEAD sealed PN0,1,2 → M4 full IPv4/TCP → actual kernel sendmmsg on unprivileged connected UDP → actual kernel recvmmsg into caller-owned slots → strict IPv4/TCP checksum/tuple/MTU validation (UNAUTHENTICATED view) → M3 AEAD+PN replay and first-only business. Kernel duplicate records are rejected. A too-small slot reports MSG_TRUNC and cannot feed parser; a ciphertext forgery with repaired TCP checksum is refused by AEAD without advancing PN; a valid subsequent record remains independent/no HOL.

**Exact SAME CODE SOURCE 12/12 triggered Actions SUCCESS**, including [r1-ipv4-tcp-native38671465556](https://github.com/lly8666/wbd-next/actions/runs/38671465556) platform **42/42**, and [r1-linux-kernel-batch-native38671465682](https://github.com/lly8666/wbd-next/actions/runs/38671465682) platform **42/42** and M0 **5/5** kernel full packet tests with compiled-once independent source-verified consumption. Other exact SOURCE checks: Governance38671465600, R0 fake platform38671465641, static38671465633, native ABI38671465603, cross ABI38671465567 **compile only**, R1 wake38671465640, normal38671465554, FEC-on38671465661, R2-auth38671465639, G2 bootstrap38671465585, all SUCCESS. Binary SHA and artifact ZIP digest under `docs/evidence/M0/R1-M4-linux-rx-batch-main-integration.json`.

## Limits and next
**REAL KERNEL I/O** here means Linux x64 GNU sendmmsg+recvmmsg over UDP sockets, not production AF_PACKET raw TCP, Npcap/Windows, Linux ARM native, real Go V4 trusted session exporter or actual system lifecycle. Raw parser fields remain UNAUTHENTICATED until M3 AEAD+PN. Product/physical/performance including sustained 500Mbps and p99/RSS/CPU remain NOT_RUN; repository phase R0_FOUNDATION_IN_PROGRESS.

Next M0 choose one separate integration atom from M1 RX ready, M2 epoch races or M3 real AEAD post-auth FEC test-only origin. Highest product blocker: verified legacy Go V4 cold authenticated session key/epoch/direction/generation handoff and AF_PACKET raw device. Four workers completed the assigned wave and await fresh formal tasks; no automatic execution is claimed.
