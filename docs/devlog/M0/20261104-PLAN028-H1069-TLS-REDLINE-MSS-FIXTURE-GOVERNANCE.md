# PLAN028 H1069｜补齐测试专属 MSS 依赖与治理证据 SOURCE

H1068 针对标准TLS原始Go框架的小Action [41689640571](https://github.com/lly8666/wbd-next/actions/runs/41689640571) 依然 **FAIL before Go test**：精简后的新夹具只复制实际执行的原Go TLS测试，但复用现成 `m0_prepare_original_go_mss_test_fixtures.py` 源锁脚本，恰好其严格原测试来源表还要读取带 `wbd_v4_native_probe` build-tag 的 `bridge_v4_probe_linux_test.go`（不会被本次普通嵌入式tag编译），缺少时报文件不存在。此轮只补该源文件以复用现成精确11处旧DefaultMSS迁移，不改变产品Go/Rust，不扩跑该probe suite。

H1068 在途已经通过 [原Go V4 TLS build+consume](https://github.com/lly8666/wbd-next/actions/runs/41689640552)、[原 Go control build+consume](https://github.com/lly8666/wbd-next/actions/runs/41689640468)，证明删除预导源码后既有冷入口可构建，但**不等于**tcpdump重组外观通过。H1068原生x86现场仍待 Go test→真实 tcpdump 及真实 UDP。

治理 [41689640185](https://github.com/lly8666/wbd-next/actions/runs/41689640185) 结构 `BLOCKED evidence is for a different SOURCE`，明确不是功能卡坏路径：H1068 cursor 错将 `last_tested_source` 改为未经产品资格的 H1067 SHA 00fdb，而 `evidence_refs` 仍唯一指向已验 H1062 source8f07 的 Windows 5/5 unit。恢复 last_tested_source 为 **8f078e...**，保留 H1068/H1069 最新候选的开发描述、checkpoint，以及未验证状态，绝不造假更新证据。feature check与结构校验因此共享同一事实。

Linux x86/x86 专项继续收证，下一独立完整 Linux 任务原生 ARM64 双端，Windows独立；旧 H1048/H1064 仅历史功能，不合规 TLS。
```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient"],"reason":"H1069 constrained TLS harness includes exact tagged source needed by donor MSS test-only migration and correctly references last source-verified H1062 evidence; pending actual TCP wire qualification."}
```
