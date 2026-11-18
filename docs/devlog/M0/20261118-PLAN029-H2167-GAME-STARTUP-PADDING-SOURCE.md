# H2167｜Game2/4 startup-padding 冷接线、真实NPF回执与WinGUI

用户授权Game2/4 startup-padding off/tls/flows实际接线及最小原生测试。历史 H2162 source 508591f Game FEC off/fixed×5政策20/20真实业务PASS_SCOPED保留，原来Game tls/flows明确NOT_WIRED，不能借原H2059 Normal padding证明Game。

H2166 [commit17c9377](https://github.com/lly8666/wbd-next/commit/17c9377e49a144de72dbb66565137247e0f8aa99) 首次自动CI真实红灯：Rust cfg字段初始化漏属性、assembly覆盖层结果blob不一致、feature目录缺此commit feature-impact。按原阈值修，不抹历史FAIL、不把source编译当业务PASS。

H2167 原Go Game TLS组认证后冷传 mode off/tls/flows到Rust V5，保留V3/V4 ABI；原Game2/4每lane M4 encrypted source seal按原20–30条/2–3秒、每record≤500B、真实物理path MTU与记录限制填充。固定FEC只拆已认证typed source真实IPv4识别，Parity/Health不填；不改AEAD/PN、Game复制竞速/FEC/重传/wire，不增Go热泵/计时器。原Rust staged密文不算真正复制，只有原Npcap syscall成功的ticket才累加padding复制记录/字节，真实owned Stop打印回执。Off不建追踪表。

WinGUI正式“传输”off/tls/flows保留保存profile/旧TLS bool迁移/重连生效；帮助去掉过时Normal-only标签，包含Game2/4，Fixed/Auto仍不扩大。原assembly manifest 3个源码create-overlay blob+3个GUI/PARAMETERS派生blob和替换锚定同步，功能卡修现行范围和签名状态。原Rust Game2源 off/tls/flows AEAD/receiver+MTU、Game4 fixed FEC source对齐的定向测试已加入源码，实际CI结果另核。

**本提交Game新原生Win2025/WSL2/原WinForms→Go→Rust NPF/双OS TCP UDP/Stop 尚NOT_RUN**；需一个源锁Game2与Game4代表测试确认。Linux发起Windows入站TCP独立NOT_RUN；完整029/029B技术出口OPEN，030 NOT_STARTED。

```feature-impact
{"kind":"updated","ids":["startup-flow-padding","gui-config-feedback"],"reason":"Wire Game2/4 startup-padding through original Go protected cold V5 and Game M4 AEAD, keep real NPF receipt plus WinGUI/help and bounded feature scope without promoting unrun native tests."}
```
