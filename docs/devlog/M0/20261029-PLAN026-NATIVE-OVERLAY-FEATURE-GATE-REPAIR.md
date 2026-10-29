# M0｜PLAN026 第一批代码的装配锁/功能卡核对

- `main@ae7afe1e` Windows Fixed/Auto Rust NativeAttachV2 首批源码提交后，自动 cheap preflight 报确切 `manifest-plan020-m0.json` 中四个 Go overlay result_blob 过期，功能目录报 `fec-auto.json` 字节超 16KiB，不能从这些错误推出真实业务失败。
- `122230fe` 仅补正四个版本化 Git blob SHA（不更改历史 original Go donor source），把 Auto 卡压成 1 字符缩进；验证 `prepare_windows_wiring.py --check-only` 的新 SOURCE cheap job 恢复 PASS。该提交没有新 devlog impact 声明而被 feature gate 拒绝，本记录以当前受影响 Auto 卡重新说明变更，保留此前失败事实。
- Rust/Go FEC2、Game、Health 的实际产品和功能/性能资格仍须依当前 PLAN026 用户授权成批后测；不将编译结果或绿灯治理转写为 Native FEC/Game/Keepalive PASS。

```feature-impact
{"kind":"updated","ids":["fec-auto"],"reason":"本次仅把此前未验证的 Windows NativeAttachV2 Auto 候选明确标识并纠正 feature card 大小与 PLAN020 Go overlay exact-blob 装配记录；不更改 Auto 用户默认或声称新功能通过。"}
```
