# S588 — recover frozen original M4 main manifest and isolate PLAN020 M0 assembly extension

S587 SOURCE b172eb63b77c0f5dac49dba91ab28cbbf16f4454: Windows2022 real native original-Go assembly + `TestM0PLAN020LiveFiveStageOSAppliedAndDisconnectedReadbacks` PASS_SCOPED Action39556612844/1 artifact12325528030. Same-source Governance39556612693 PASS. Governance Maintenance39556612680/1 **FAIL**, two exact frozen Windows manifest tests: original `r0/go_overlay/assembly/manifest.json` blob expected `ebe2beac0aa5317eddf3c2d7db5d833d48ea01eb`/37 ops; M0 altered it to `2ef8a885a1cbd6311e876baf0971a74c827fac97`/39 ops. No product release qualification.

Repair: restore frozen original main manifest byte-for-byte to `ebe2beac...` and place M0 additional Windows live OS receipt tests/WinForms truthful READY patch in distinct `r0/go_overlay/assembly/manifest-plan020-m0.json`. Only this M0 Windows2022 gate opts into extension. All other donor/current workflows continue consuming original frozen manifest. Do not touch the frozen M4 branch or actor cursor. Previously failed workflow runs 39555998587, 39556113464, 39556357188 and this maintenance FAIL retained unchanged; positive scoped Action39556612844 does not become product Applied.

This is S recovery before H; next exact-source Actions must confirm maintenance regression and special Windows assembly both pass.
