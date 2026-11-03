# H1021｜H1020真实原Go自动租约UDP 5/5通过，Stop/共享TUN证据FAIL：保留原进程日志定位

H1020 SOURCE `784e4d3f5560039f691124a2d322cb09f425096f` `PLAN012-COMBINED-REAL-GO` Action `41587460751`，native job `125756182495` **FAIL**。原Go受保护TLS自动/32、Rust M4双netns UDP应用回显 `M0_PUBLIC_ORIGINAL_GO_V4_CLIENT_SERVER_RUST_M4_REAL_TUN_UDP_ECHO_OK 0..4` 全部可见；原脚本后续真实原生Stop/OS回读段退出码1，未打印新的 `M0_PLAN028_REAL_AUTO_LEASE_NATIVE_IP_BOUND_PASS`，无法宣称单设备完整Stop PASS，后续三netns A+B尚未执行。此轮脚本临时删除TLS客户端/服务端日志，只上传业务输出，源锁无法从历史日志判定是客户端原生Stop、服务端每session Stop、OS进程退出或Rust共享TUN reader join哪一环失败。

H1021修正**失败可诊断性而不改变业务代码**：在既有临时日志删除/清理前，且只当自动租约原生测试实际失败，导出有限的两端 `V4_PUBLIC_` / Rust native Stop / OS readback / 错误分类日志（credential/password/secret/key等关键词值脱敏）至该原生Action同源artifact；同时输出进程是否还活着。绝不保存TLS密钥、密码、完整握手、pcap或业务payload。原有完全相同的失败条件仍检查原TLS、真实应用5/5、设备 /32、单Rust reader `routed>=5`、`reader_joined=1`、客户端/服务端独立Stop；正常情况下无诊断文件。该修复目的只为得到能够直接修产品的准确故障而非反复盲猜。

H1017单client旧SOURCE9c39完整原native PASS仍真实；H1019/H1020新并发manager版本未完成原生Stop和多设备业务验收，保持FAIL/NOT_RUN。Windows/WSL2 Game4 lane2旧FAIL和H998物理MTU/ARM64 Game4FEC旧FAIL均保留。

```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient"],"reason":"Capture minimal redacted actual Go+Rust native Stop/OS status on auto-leased shared TUN failure before CI cleanup; no change in product, pass criteria, or failed-source promotion."}
```
