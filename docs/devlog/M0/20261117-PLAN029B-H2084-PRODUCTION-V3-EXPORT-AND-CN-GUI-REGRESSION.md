# PLAN029B H2084｜修原生发布DLL V3缺失的首个真网络故障，并回归新旧CN配置

H2083 `SOURCE=12db9e2464c52e149b94701ac258d4b1a2f1fa34` 的 Windows Go编译、Rust Windows/Linux单测、正式 Linux Go/Rust 对端和governance均PASS；自动 Action [44045024679](https://github.com/lly8666/wbd-next/actions/runs/44045024679) 是**真的**Windows2025签名Wintun/Npcap↔WSL2，但客户端报 `Failed to find wbd_m0_win_native_v3_start procedure` 而在OS Ready前退出，Action **FAIL**，没有实际应用业务资格。原因很明确：029B off/all需保留Rust V3公共DNS/填充，原 `.github/workflows/m0-wl-public-normal-full.yml` 却只在标记了旧029 private CN试验时给 release DLL 加 `m0_v4_probe`，默认构建无V3导出。**不回退Go至旧V2，不伪造Ready。**

H2084 按当前新产品统一常驻的V3 ABI，在原release DLL features加`m0_v4_probe`，不更改wire/TLS/FEC/认证；在每个真正Windows product DLL创建后，无论显式试验与否，用Python WinDLL加载验证`wbd_m0_win_native_v3_start`，在打开真实driver前fail-closed。历史二进制仍按原SHA标记，旧H2083失败保留。

本次又把新常规CN纯组件测试写入原Rust代码：UDP53/TCP53 的真实 `198.51.100.23` A/TTL2/原事务ID在`cn-domain-direct=false`不创建Fake池/写者时原样回包，错ID拒收；高级CN原FakeIP写入单测保持不变。此前H2077的原WinForms高级FakeIP实网夹具现在**显式**选`--cn-domain-direct=true`，否则新fresh false会错测成普通模式；Python GUI桥正确传Bool到原PortableStore和Go child，最终原GUI effective加该字段核验。纯GUI夹具同时核验全新false、旧保存JSON缺键迁移true、显式false不可翻转。以上仍需新SOURCE CI和原生回执，不借H2077历史真通过替代029B B2/B3/B5资格。

不启动旧028七模式矩阵，不重跑H2070探针，依据真实首个问题收一个新固定SOURCE Normal签名网络结果。

```feature-impact
{"kind":"none","ids":[],"reason":"H2084 repairs release-workflow Rust V3 ABI selection and adds ordinary/advanced CN and GUI regression fixtures; no feature catalog contract definition changed"}
```
