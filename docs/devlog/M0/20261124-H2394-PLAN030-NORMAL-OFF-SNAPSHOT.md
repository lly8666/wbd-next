# H2394 PLAN030 Normal/off snapshot

45355353310 reached second native GUI connection and actual server roster: remote port 41032, online Normal, correct lease/identity, authenticated 1420/1420 record limits and actual RX/TX 172/180. Assertion failed because negotiated_inner_cap=null and fec empty. Normal off has no FEC owner; OriginalFECReadback rejects nil FEC. Reuse authenticated cold policy solely for Normal/off and existing Rust budget ABI; leave unknown remote OS and other unavailable fields unknown. Add snapshot budget regression and rerun the existing domain combination. Earlier Linux CLI/watch results remain source-scoped; no data-plane changes. New candidate unverified.

```feature-impact
{"kind":"updated","ids":["server-management-cli"],"reason":"实际第二代重连与快照已达，修Normal/off无FEC owner造成内层协商预算遗漏。"}
```
