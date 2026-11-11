# PLAN028 H1613｜两场并行原生生命周期经原始Artifact确认，冷启动与Stop均实证

同一正式产品二进制SOURCE `8a31375e36bb6a93860c5579e64b4a39d0b6e346`，原始Go TLS/FakeTCP与Rust native ISA-L x86_64三个实体hash与H1600成功Action`43027983611`完全相同，H1611/H1612均**没有重新编译**，从H1600到当前代码和原真实netns fixture零diff；测试SOURCE分别`c066edd4`和`44593a822f29d2d87b896349b0b9a41159de1a18`，不可冒充新SOURCE新build。

- [H1611 idle100 Action43050188977](https://github.com/lly8666/wbd-next/actions/runs/43050188977) **SUCCESS**；原ZIP artifact `13869171897` SHA256 `e3a61b7382fcdfc16b28ce640d1e00e0eb8a6579882f270fedd187b2b0b57e0b`；真实Linux原Go TLS/Rust TUN FEC Auto**显式选项**双端 `mode=auto applied=1 profile=5` 读回。64个初始真UDP已到，无业务100秒后1个新真UDP回声、原Native Stop全通过（原native log hash `c1910572...`），不代表Health能够代替业务恢复或FEC自动质量收敛。
- [H1611 dead106 Action43050188879](https://github.com/lly8666/wbd-next/actions/runs/43050188879) **原始FAIL**，artifact`13867444602` ZIP SHA `5482d7641eb97e20be8acc83c0880625a6ad5e3dd8d46e2b8a087a6139ff57a9`；最初64真UDP交付后，本来应进入106秒双向物理100%丢包检查，却由旧PLAN026临时夹具要求Rust不再输出的过期reason串而先失败。它没有证明后续业务或Stop；**不得覆盖原FAIL**。
- H1612仅更正临时夹具中精确Health事件字符串、保留完整硬门并输出脱敏原native events后，[定向dead106 Action43053067266](https://github.com/lly8666/wbd-next/actions/runs/43053067266) 整体 **SUCCESS**，artifact`13870247251` ZIP SHA256 `b44657c62ff05f27a7f06a52d031048b87b1e7c74fa5271a0ea26cb33c89ffe2`；客户端和服务端原始日志都明确有 `WBD_M0_NATIVE_HEALTH_TIMEOUT side=tx reason=authenticated_dead_or_peer_retired`，旧native Stop、`dead_drained`、`NATIVE_DEAD_RECONNECT_ARMED generation=1`，真实TUN新业务触发客户端 `NATIVE_RECONNECT_TRIGGER generation=2`，真实原Go TLS/SYN后双端第二次 `NATIVE_READY`，恢复后1个真kernel UDP echo，最终双端第二次 `NATIVE_STOP_DRAINED`。旧Go客户端/服务端PID未手工杀掉，106秒真正双端 netem loss100%，实际qdisc drop正值由原夹具严格assert（**原始绝对丢包数未收集**）。复验原 native 客户端事件log hash`e66b5cac...`、服务端`02f4c3a5...`，更详细见 [H1613 JSON](../../evidence/M0/PLAN028-H1613-IDLE100-DEAD106-PREBUILT-X86-NATIVE-SCOPED-20261111.json)。

**范围**：两个Linux x86_64短真实内核原生生命周期资格 `PASS_SCOPED`，不等价于Windows当前SOURCE新认证路径的idle/失联、物理公网、L3、近derived MTU大包或CPU p99。FEC Auto仅显式测试，产品默认仍**Off**；Windows15s/90s/idle0、Linux默认rotation0仍未改变。H1602 nearMTU按用户明确跳过，原环境失败保留；同主机多Wintun用户排除。PLAN028依旧`IN_PROGRESS`。

```feature-impact
{"kind":"updated","ids":["idle-rotation-keepalive"],"reason":"Add source-locked authentic same-product prebuilt idle100 and dead106 original TLS Rust Health/reauth business/Stop receipts and retained prior failure without changing shipping code."}
```
