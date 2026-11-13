# PLAN029 H1755｜H1754真实COM首错已收，下一步定位精确字段

- `fc83135a43c98cee5e3acc97c49c85dd78e1c0f8` [Windows Action43437539407](https://github.com/lly8666/wbd-next/actions/runs/43437539407) 真实Windows2025运行：original Go装配/编译/纯测试 PASS；原生Defender COM单规则 Add/readback FAIL `unconfirmed route ownership; retain journal and fail closed`，finally清理亦报同错，WAL未删。Governance 43437539285/43437539234 PASS。H1753格式错误零job FAIL独立留证。
- 当前不能区分COM规则缺失与哪项属性被Windows规范化；也非新Wintun网络失败。根据 Microsoft INetFwRule 每项设置即时验证/回读规则，H1755仅增加原严格匹配比较的首个字段差异，并把COM源路径加进旧H1661 workflow触发，不增Action场景、不做Allow放宽。
- Lookup及RemoveOwned仍仅接受全部字段完全一致；意图WAL/owned CAS/失败保留不变。H1755新SOURCE实际CI待测；下一步以首个COM字段决定修复。正式Rust kernel TCP及D1–D5/P1–P2、padding、GUI未验；028限定收口、030不开工。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Native H1754 Defender COM fail preserved; H1755 strict readback first-field diagnostic, CI pending"}
```
