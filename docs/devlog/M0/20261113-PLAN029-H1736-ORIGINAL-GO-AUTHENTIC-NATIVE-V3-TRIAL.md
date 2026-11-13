# PLAN029 H1736｜原Go认证NativeOwner接入严格限定的Rust V3试验门

- H1735 `ddcf09766348ab4cd6f33c1fcb05a09ddc05d27b` [Rust Windows/Linux Action 43403058114](https://github.com/lly8666/wbd-next/actions/runs/43403058114) 双job **SUCCESS_SCOPED**：Windows2025 platform46、Rust PLAN029 55、private V3 probe56；Ubuntu24.04 platform115、Rust PLAN029 45。不能用这些pure native结果冒充真实分流联网。
- 本批在**原凭据验证Go TLS→签名Wintun/NPF→Rust authenticated NativePeer**冷 `BindNativeRing` 时，只有GitHub Actions当前SOURCE且明确 `WBD_PLAN029_NATIVE_V3_TRIAL=1` 才选私有`StartNativeIOWithColdSplitProbe`；普通GUI/CLI仍走既有V2，不凭空发029 Ready。源网络Plan/Go TLS/当前代 owner/Stop/WAL入口不绕过。
- CN模式试验强制明确`WBD_PLAN029_CN_RULES_FILE`绝对路径、真实regular文件、大小1..1MiB，拒绝symlink、缺文件与不支持的include/regex/keyword等语法；`m0Plan029ColdSource`检验物理绑定、lease、inner MTU、单值DNS、Direct/CN/LAN、FakeJournal绝对地址。All/BypassLan不建CN fake journal。新Go Windows用例覆盖CI隔离/缺规则fail-closed/合法域名cold/readback。manifest四个Go overlay live blob SHA同步。
- 本提交只是**可启动真实试验的产品接线SOURCE**，从未运行真实V3签名Windows D1–D5/P1–P2；Direct kernel TCP actor与精确Defender、DNS UDP截断→同endpoint TCP、full geosite v2fly、bounded padding、GUI live effective和owned恢复仍需实施。CI结果等待source-frozen Actions，保留失败及028限定收口，不开启030。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Wire original credential-authenticated Go NativePeer to explicitly gated private Rust V3 cold split trial with validated CN geosite file and same generation Wintun/NPF ownership; actual 029 networking remains NOT_RUN"}
```
