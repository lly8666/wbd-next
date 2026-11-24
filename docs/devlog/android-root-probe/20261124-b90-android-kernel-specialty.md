# B90｜七模式预认证收口；真实 Android 内核及物理 DNS 专项

B89 SOURCE `3cba0860e93606a5559955bd74eff4b4263d2ffe` [Action 45406291224](https://github.com/lly8666/wbd-next/actions/runs/45406291224) 9 SUCCESS/2 FAILURE/6 SKIPPED；[KSU Job 138490237533](https://github.com/lly8666/wbd-next/actions/runs/45406291224/job/138490237533) 七种模式各 preauth=PASS cleanup=PASS，独立 Bionic 原 TLS 功能 PASS；[artifact 14925387531](https://github.com/lly8666/wbd-next/actions/runs/45406291224/artifacts/14925387531)。不冒称 peer TLS、认证租约或 M4 PASS。两失败 Job 共同源于 linux-original-oracle.sh 错误插入重复旧 Oracle 代码与引号。本批修复，不重跑 Linux 性能矩阵或七模式。M0 cursor/evidence 不一致归 main，不改。

B90 只改 CI/夹具/文档：一次 Android16 x86 KSU boot，不启动 FakeTCP 服务器。CI-only Go helper 在正式 ELF 完成后调用原 openTun、rootjournal、原 ip 批量安装完整 CN CIDR；真实 PackageManager UID、single/group/all+排除、真实普通 App UDP→TUN、原 Stop 恢复。独立 DNS 使用 Activity 真 PhysicalNetwork scope，原 Bionic netd 物理 UDP53 和 TC→同 Network TCP53，host 可控本地 DNS fixture。组件测试 /32 不是认证租约。系统 Resolver、隧道 DNS、认证后 Go→Rust handoff、实际切网仍后续独立测试；不做性能测试/额外防御/新产品功能。B90 待 Actions。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"Accept B89 seven-mode preauth/cleanup and Bionic TLS evidence; repair CI script and test actual Android kernel UID/CN/Stop and scoped physical DNS without repeating seven modes."}
```
