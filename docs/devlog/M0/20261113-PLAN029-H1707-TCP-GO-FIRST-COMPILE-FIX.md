# PLAN029 H1707｜H1706 Go 夹具编译首错定向修复

[H1706 Action43357897035](https://github.com/lly8666/wbd-next/actions/runs/43357897035) SOURCE38669421 **FAIL before network**：Rust DLL编译、pinned donor与装配已成功，Go test-only文件 unused `errors` import + `rc`重声明。原环境未执行签名Wintun app SYN、Linux guest、Defender/WFP或路由变更。不是内核TCP后端或网络出口已经失败。历史FAIL保留。

只移除未用的 `errors` 导入，FFI `rc`改名 `trialRC` 和相关结果引用，其余Rust NAT、WinSock TCP、监听器、owned生命周期不修改。H1707由原一场景路径触发，真实成功或首错另验。保留H1704真实跨Linux Wintun Rust UDP回程PASS和H1697无旧WFP Win32 PASS。029 Normal/Game4产品DNS/FakeIP/GUI/padding D1–D5/P1–P2未合格。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6","windows-native-transport"],"reason":"Retain first H1706 exact-source Go test-only compiler failure, repair unused import and duplicate rc before real TCP kernel/guest qualification."}
```
