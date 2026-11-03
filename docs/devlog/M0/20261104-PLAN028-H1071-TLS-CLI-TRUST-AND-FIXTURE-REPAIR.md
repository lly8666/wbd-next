# PLAN028 H1071｜真正接通TLS证书信任与离线route-key，窄收CI回归

基线为 H1070 原产品SOURCE `743e026e2723d20c1c09e1cd5c5f8a2bbe6c2536`。先收在途 Actions：x86 真内核 [41690743091](https://github.com/lly8666/wbd-next/actions/runs/41690743091) 在首个 TLS 验收前 `flag provided but not defined: -tls-ca-pem`，因公共 Go V4 Linux parser 尚未接线（而真实 tls.Config RootCAs 原先已装配）；[Windows WAL 41690742952](https://github.com/lly8666/wbd-next/actions/runs/41690742952) 的真原 Go TLS 自签证书直接失败 `x509: certificate signed by unknown authority`，这是新强制验证的正确 fail-closed 行为，夹具需要导入应用专属 CA。[Windows/Linux 41690742974](https://github.com/lly8666/wbd-next/actions/runs/41690742974) Win Go编译与Win/Linux Rust单测成功，原 Linux构建因旧安装脚本把已有 `tls.go` 当新文件拒绝覆盖而失败；[原 Go TLS consume 41690742842](https://github.com/lly8666/wbd-next/actions/runs/41690742842) 编译成功、在测试 Mock owner 的 MSS 断言失败；原 feature catalog 要求更新卡；治理退化例 `EXPECTED` 从4/11迁移到3/10 未同步。以上不构成 TCP 首载荷/标准报文合格证据。

H1071 在**同一个产品/测试 SOURCE** 内：
- Linux `v4productcli` 普通+Game 入口强制离线32B route-key，缺失/错长在打开 raw/TUN 前本地拒绝；`--tls-ca-pem` 加载应用专属私有 x509.CertPool（不写系统信任、不关闭TLS验证），默认系统可信根。已有 `--route-key-hex-file` 和服务端一次性 `--init-route-key-file` 产生0600随机32B材料原样保留。
- Windows 原 Go+Rust Wintun集成测试固定本次自签证书，导入测试客户端RootCAs；**不准改回 InsecureSkipVerify**。Windows产品及GUI配置 H1067 原接线保留。
- 原 Go FakeTCP 私有 owner 单测比对真实 `PublicV4AdvertisedMSS()` 的 SYN 协商值，不把某个旧测试会话的初始值冒充固定1460外层/MSS1420；独立真实SYN测试仍保证后者。旧 MSS 迁移测试修正为精确三文件10次。Linux双OS装配对已经有的 `tls.go` 先核 donor Git blob `518a...` 后按原 plan020 manifest 覆盖，不绕过源锁。
- `manifest-plan020-m0.json` 精确同步源 hash；不动 Rust steady/FEC/Game 算法或 wire，也不重新派发历史失败场景。

**限制**：本提交是SOURCE candidate。原WB-R1功能PASS属于违反建链契约的旧SOURCE，必须继续记录但不升级报文外观资格。只有新 x86/x86 实际 ClientHello TCP重组（服务端无先发、完整TLS record、动态SessionID/扩展）+证书、密码反例、Rust IO/Stop与Windows受限入口证据核实后才能升级；后续Linux完整任务ARM64双端。H998在线MTU缩窄FAIL、旧ARM64 Game4FEC FAIL、Windows物理NIC NOT_RUN、CPU/p99因果与remote ICMP未证原样。

```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient"],"reason":"H1071 connect mandatory pre-shared route key and app-scoped TLS trust across Linux Normal/Game, Windows self-signed test trust, original TLS donor source installer and exact MSS tests; native wire/Windows pending source-locked CI."}
```
