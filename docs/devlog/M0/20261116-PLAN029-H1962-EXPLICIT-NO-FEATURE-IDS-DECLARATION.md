# PLAN029 H1962｜feature-impact none 的 IDs 空数组显式化

- H1961 原 exact-Go assembly manifest 2项已修复，原 [Action43796550766](https://github.com/lly8666/wbd-next/actions/runs/43796550766) `--check-only` cheap PASS，Windows源码编译启动；[Action43796550763](https://github.com/lly8666/wbd-next/actions/runs/43796550763) 主治理 PASS，但 Feature catalog 的 `feature-impact` 明确要求所有声明都带 `ids` list，`kind:none` 必须 `ids:[]`。这是文档声明格式失败，并非原生Go功能或实际 DNS 失败。
- 修正 H1961 devlog 的 JSON `"ids":[]`；不改原 Go/Rust、manifest pin、DNS出口、GUI、scene flags、任何已保存证据。不因 H1962 新一次提交派发真实 WSL2 P2。普通产品早连仍 OFF。
- D1/D2 一切原 Win/WSL2 真实限定PASS来自 H1958 SOURCE `ab224ae...`；其他 D1–D5/GUI/Game4/IPv6/P1-P2仍 OPEN。

```feature-impact
{"kind":"none","ids":[],"reason":"Correct only the previous no-feature-impact declaration to include an explicit empty ID list; no product code or verified status changes."}
```
