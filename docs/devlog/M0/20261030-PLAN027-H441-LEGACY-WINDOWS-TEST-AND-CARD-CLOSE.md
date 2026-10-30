# PLAN027 H441｜退役M2后两条过时 Windows 正例测试与卡容量修复

H440源016b249a真实编译后收到 [Actions40985293722](https://github.com/lly8666/wbd-next/actions/runs/40985293722) / [40985293773](https://github.com/lly8666/wbd-next/actions/runs/40985293773) Windows Rust整库可编译，但旧Fixed6 tests在 `v4_windows_fec2_owner.rs:1013,1247` 仍要求逐record Receipt `Some(...)`；产品新要求明确不允许此输出。H441保留真实Rust原M1/driver-firstsend、FEC parity连续Seq、冻结Shadow、Stop、安全身份这两条回归的核心检查，将旧Receipt期待改为 `Ok(None)`，同时本源没有outer ACK时不能伪退休冻结Shadow。未忽略测试、未放宽PN/SEQ。原 Normal/common legacy Action40985294022 FAIL 另外保留，不能冒充已修。

治理源40985293756 feature catalog失败因 `fec-auto.json` 16574B > 16384B，压缩与 verification 重复的SOURCE4977f说明（原 verification/失败证据照存），新卡尺寸 16350B。本批仅tests/卡/留痕；PLAN027 A/B/C及5min和确切SOURCE的真实Windows/Linux验收均未齐，不报全完成。

```feature-impact
{"kind":"updated","ids":["fec-auto"],"reason":"Keep bounded Auto card by shortening duplicate historical limitation; real source verification entries and failures remain unchanged."}
```
