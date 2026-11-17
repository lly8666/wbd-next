# PLAN029 H2044｜首个装配边界与 H2043 治理失败，修复但不改写历史

- H2042 新 Windows 原生 Action [43992426014](https://github.com/lly8666/wbd-next/actions/runs/43992426014) 首个失败是 pinned `native_dns_bootstrap_windows.go` 的 overlay blob 与锁不一致，Go 编译/真实网络未运行；H2043 已修正该 blob，但 [43992703610](https://github.com/lly8666/wbd-next/actions/runs/43992703610) 下一层首个失败是 `native_dns_bootstrap_windows_test.go` 锁未更新。H2044 仅补此一条精确 blob，不清理未知更改。
- H2043 同时修复 TCP 回退共享解析器三返回值编译接线、把 FakeIP journal 加入既有两 OS Rust 组件 workflow 触发；H2043 由于缺少新 devlog feature-impact 与 cursor context_refs 超界触发治理 FAIL。现补短记录与 bounded cursor。两个原 FAIL 保留，不冒充通过。
- 当前真正 WinForms `ClientSession.StartAsync/StopAsync`→真实有签名网卡业务与小额度 DNS/Direct/TCP pressure 仍待 SOURCE 锁验证；已通过 H2031 padding/H2041 Game4 不重复派发。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"H2042–44 fix native bootstrap source locks, same-endpoint TCP parser and async writer pressure test trigger, evidence remains unverified until source-locked jobs complete."}
```
