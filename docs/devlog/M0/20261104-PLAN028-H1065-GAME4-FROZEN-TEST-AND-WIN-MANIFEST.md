# PLAN028 H1065｜x86 原生 Game4FEC6 切网真实业务已出现，修正错套的 Normal 测试资格

[H1064 SOURCE2943 Action 41680333332](https://github.com/lly8666/wbd-next/actions/runs/41680333332) 原生两 Linux/x86_64 同架构端点真实原 Go TLS、Rust Game4 fixed6、veth/AF_PACKET/TUN：client物理出口OS源IPv4从10.25.0.2切到10.25.0.3，内层MTU真实读回1358→1178，用户外层默认1460、出口物理1280。同安装受保护 /32 一直是10.66.0.238/32，旧 client Rust Game M4 与 raw 完全 Stop 后新4 lane TLS/Game组重新认证，同一server 443、Rust端原旧group被准确 `same-protected-cohort-new-generation` 退休。新组5个真实内层UDP回应通过，旧新组原 Rust FEC6 的 `parity_copied` 非零（不是请求档位）。**这只是先断再连顺序恢复，不是健康 Game lane 重叠无中断。**

整条原 Action 仍为 FAILURE，原因已定位为此前 Normal auto-IP fixture `V4_PUBLIC_SHARED_TUN_READER_READY role=client` / client `V4_PUBLIC_SHARED_TUN_STOP_DRAINED` 断言套给 Game：Game client 没有多group shared TUN fanout，本阶段 old Game group M4 reader 完整 Stop 后才允许新group reader；server 一直只有一个原 Rust shared TUN reader。修改原 fixture 为 Game 特定**强**断言：客户端两代 original Rust stop 先于新 candidate、服务端 shared TUN 已路由10个实际包/最终 ReaderJoin=1、旧 cohort Stop仅一次，双方两次 Game4FEC6 parity_copied>0。保持 Normal 原断言不变。

**不重复编译源**：新 [H1065 frozen workflow](../../../../.github/workflows/m0-plan028-linux-game4-path-frozen.yml) 直接下载 H1064 artifact `13251334641` 中确切SOURCE 2943的Go client/server和Rust.so，核真实ELF及 SHA256/原 donor，单一 x86/x86 真内核切网场景；不复跑旧1%/Health90/多模式矩阵。两个失败的 Windows preflight/Win WAL Action 因为共享 `r0/.../v4productcli/linux.go` 的 Windows `manifest-plan020-m0.json` hash 仍指向旧blob，现只同步新 overlay `result_blob=c8a2...`，不绕过装配审计；没有新 Windows 产品改动，也不得说原 Windows NIC/IPv4 物理切网通过。

证据 `docs/evidence/M0/PLAN028-H1065-SOURCE2943-GAME4-X86-IO-AND-HARNESS-FAIL-20261104.json`。Windows物理切网、Game真正健康lane并存、ARM64 Game4FEC旧FAIL、H998在线热缩MTU FAIL、remote ICMP、CPU/p99仍限定未通过或未测。平台轮换：这次Linux任务为x86两端，下一次Linux新任务ARM64两端。

```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient"],"reason":"H1065 exact H1064 native x86/x86 Game4 fixed6 path app/Stop/MTU observations, correct mistaken Normal client shared-TUN assertion, reuse frozen binaries; sync Windows manifest original Go linux overlay pin."}
```
