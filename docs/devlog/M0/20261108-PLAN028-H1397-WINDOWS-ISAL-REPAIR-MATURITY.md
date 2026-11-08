# PLAN028 H1397｜Windows真实 Fixed/Auto FEC 默认 ISA-L 漏接及 owner 成熟单测

2026-11-08。原 [Action42481748620](https://github.com/lly8666/wbd-next/actions/runs/42481748620) 是 CI FAIL，但实际 Windows2025 MSVC 已用 vswhere 找到原生编译器，官方固定 ISA-L `c387163fcbca62701d646149564c550c78a4f985` `isa-l_static.lib` 构建成功，`native_fec_acceleration` 正式 release Rust DLL 构建也成功。之后 owner 模块 73 tests 72 PASS／1 FAIL，**签名 Npcap/Wintun/真实原应用与 Stop 在该 Action 都 NOT_RUN**，绝不偷换为功能 PASS。

失败原测试 `m0_windows_auto_mature_667pps_drains_all_real_2s8s_deadlines` 模拟 700 FirstSend×(2s+8s)=1400 个原到期事件；现行 `drain_original_auto_mature_due` 每次调用最多 256 events **或 200µs**，属于防一个 client 拖延兄弟的真实锁公平限制。旧测试硬编码 16 次 owner 回调必须全部完成，在 Windows runner 上真实只到 324，故失败不能认成实际 667PPS 处理上限。新测试每次必须有单调进展、最多 256 bounded turns，原要求每窗 700、UNKNOWN 700、无伪 M2 Applied、幂等及原 Stop/Release 不变；不改正式产品 200µs、协议、主动心跳、owner 调度。

另经原 Go→Rust ABI 真调用链发现 `v4_windows_fec2_owner.rs::encode_repair_entry` 原本硬编码 `BackendChoice::Scalar`，意味着原 Windows Normal/Fixed/Auto FEC 即使静态链接 ISA-L也被强制关闭。现仅改为既有 `BackendChoice::default()=PreferNative`，返回内部 `BackendUsed` 供单测，导出 C ABI 保持原样；小于 64B、单 source、无 native 编译仍可合法 scalar。新增经过原 authenticated Windows feature7 Entry 的 k2×160B 确实走 ISA-L 且原修复记录字节与 scalar 完全一致的单测，并保留原 Stop/Release。无 Go 热泵/额外 header/新 FEC 算法。

明确：新源码真实签名 Windows Action **待收**；不能用构建＋unit 冒充业务；复用 ARM64 L3 2×1800 PASS_SCOPED、x86 原物理黑洞离线 PASS，原失败继续归档。

```feature-impact
{"kind":"none","ids":[],"reason":"Frozen PLAN028 repair of proven Windows FEC parity backend wiring and timed-fixture fairness assertion; no user-facing API/wire/record feature change."}
```
