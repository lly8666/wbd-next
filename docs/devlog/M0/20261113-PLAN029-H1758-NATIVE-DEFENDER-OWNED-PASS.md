# PLAN029 H1758｜真Windows Defender owned CAS单规则PASS_SCOPED
- H1757 SOURCE `9b9b1902a400478d19d1985e6e3732f8093aa8b4` [Windows Action43442086701](https://github.com/lly8666/wbd-next/actions/runs/43442086701) genuine IN/TCP exact one-lease/one-remote/one-port Defender COM Add→readback→owned CAS Delete **PASS**，Go装配+编译PASS。无产品TCP连接，不当成双出口/Ready合格。
- H1754/H1756旧native COM FAIL、H1755 SOURCE装配FAIL均保留；H1757 [治理43442086632](https://github.com/lly8666/wbd-next/actions/runs/43442086632)结构FAIL `evidence is for a different SOURCE`，原因是cursor所引用证据只有`tested_source_sha`而缺要求的`source_sha`。本提交只新增正向源锁证据和更新M0 cursor，避免重复dispatch。
- 下一步真实产品post-Apply PREPARE→准确owned Defender→Rust ENABLE→Stop，然后D1–D5/P1–P2和GUI/padding。029未完成，030未开工。

```feature-impact
{"kind":"none","reason":"Only M0 cursor and source-locked evidence of H1757 existing scoped native Defender COM test; no feature source or card changed"}
```
