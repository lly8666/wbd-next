# M0 S263 intent — continuous release-code FEC2 receiving owner

Recovery H191 checkpoint 81de053d439a39ef14116f72dc680f4aa967ac16, only H191 cursor change through main2a5ff3b3f36a46fd67733d39efbd5ed0f2ca1c83; task unchanged rev2/epoch1. H191 Governance39276437599 PASS. Several uncompleted worker-dispatch actions on unchanged main (39277346874 pending, 39277279598 in_progress) plus unrelated H191 scope audits; no concurrent M0 main branch source changes. Earlier exact-source combined 39275492225 SUCCESS release-code FEC record 3 suites, M1 Game2/4 native, original Go kernel one block; NOT multi-block production. Explicit current user requests production FEC2 after qualification.

First core integration component is a persistent, bounded, real release-code FEC2 peer receive owner independent of private probe:
- Construct ONLY with Go-approved original exporter S2C direction keys and suite under opt-in `fec2_product_record`; API itself does not prove Go grant, never turns FEC2 on. Reuse same original ReplayProtectedLaneRx, do not copy per-block PN bitmap.
- Accept real authenticated source(kind2)/repair(kind3), bounded interleaved multi-block ID windows, no cross-block HOL; receiver returns candidate first valid sources and RS16 recovered missing business frames distinctly, not a native TUN delivery claim. Late replay/stale epoch/policy and incorrect actual_k fail closed, bounded memory and Stop clear.
- Tests are compiled in ordinary release option (not probe/test-private) across three suites, interleave 3+ blocks and drop/corrupt/replay, under native one-job functional with both old and new record crypto. Default release remains FEC2 OFF.
- Later SAME original Go TLS credentialed persistent background M4 raw TX/RX owner and true TUN recovery required for full product; Game2/4 real lanes, Auto M2 mature, Stop/MTU, CLI readback still hard gates. No product enable until all pass. If this turn does not achieve entire product, H records PARTIAL and OFF, no false applied.

Existing main dispatch runs may finish while work proceeds; reconcile before H.
