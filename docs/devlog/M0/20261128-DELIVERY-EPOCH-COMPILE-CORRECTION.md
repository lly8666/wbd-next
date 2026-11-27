# M0 delivery epoch compile correction

117d0f8 exact native46032634286 x86 job140620018234 and ARM job140620017755 both failed product compilation at rate.rs:89: functions are not allowed in struct definitions; E0599 at conn.rs:1281 follows from misplaced accessor. My previous source edit put epoch_preserved() in struct Rate rather than impl Rate. No core test, no native product, no three-host performance measurement (46032634335 prepare140620017483 failed, three execution jobs skipped). Preserve failed attempt; no rerun same broken SOURCE. Move accessor into impl Rate, Default derives counter initialization, TxState sample fields public, regression uses existing scoreboard API and clock math. No product behavior or algorithm changes from intended previous candidate; no new knob, protocol or HOL. Existing source ABBA unchanged; no performance claim. Historical branch governance remains separate.

```feature-impact
{"kind":"updated","ids":["dual-rust-tcp"],"reason":"Record exact dual ISA compile failure and correct misplaced accessor; keep original source comparison."}
```
