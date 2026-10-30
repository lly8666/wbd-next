# H490 original Linux FQ really drops ZERO, next original TUN link counters

H489 original same-source binaries (H485 build Action41013628666, frozen f83874c30e0d918cfe070b67b39e208eea0da457) signed two-OS 60s Actions41019395006 and41019397183 both owned Stop and near-target actual bidirectional 100M and 75M offer. Windows first missing254 at 100M pure1200B, 412 at 75M mixed; Linux side first100%. Original Linux server TUN ingress normalized against exact same C10 source control deficit249/415 respectively, matching Windows missing to 5/3. This supports a Linux pre-M1/TUN path, not a Windows UDP-buffer root, but aggregate cross-session counts are not individual packet provenance.

**Actual original WSL root `fq` qdisc raw `tc -s -j` before/after artifacts show drops_delta=0 in BOTH scenes.** Its counters are at top level `{"kind":"fq","drops":0,"packets":...}`, not the nested `stats` used by the first parser. H490 corrects the parser and adds regression from exact kernel shape; restores measured FQ0, no fabricated queue loss or blind FQ flow_limit expansion.

Next inspect separate Linux TUN netdevice `ip -s -j link show dev wbdwl4` `tx.dropped/rx.dropped` snapshots, which are NOT FQ counters. One genuine original Windows↔Linux C100 mixed scene, same product binaries/source; all process PID and Stop contract preserved. **No proven complete 0-loss at C100; PLAN027 partial.**

