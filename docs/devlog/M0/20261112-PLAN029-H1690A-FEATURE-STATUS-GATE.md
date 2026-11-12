# PLAN029 H1690a｜真实 FAIL 证据不变，修复功能目录单提交声明

- [H1690 signed native source](https://github.com/lly8666/wbd-next/actions/runs/43243971440) **FAIL** 不变：原生 listener 可本机连接，签名 Wintun 注入 UDP 没有到达；TCP SYNACK 仍缺失，未启用任何 WFP/Defender 修改。
- H1690 入库首个功能卡状态误用了非枚举 `FUNCTIONAL_FAIL`；随后的单文件修正为允许的 `FAIL`，但 [Governance 43245397976](https://github.com/lly8666/wbd-next/actions/runs/43245397976) 的 Feature catalog 根据单次提交 diff 要求 **功能卡变更和 feature-impact devlog 同提交**，因此拒绝了单卡修复。新提交把两者成对归档，不修改产品代码/网测或真实证据，也不重派 Windows 测试。
- H1686 GUI 错误、H1669/H1672 真实签名 Windows TCP 错误、H1690 UDP 失败均保留，不迁移为 PASS；029 产品出口仍未验收。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Pair catalog FAIL status scope note with required changed devlog after H1690 native diagnostic; no product readiness promotion."}
```
