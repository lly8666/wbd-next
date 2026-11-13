# PLAN029 H1744｜首个原Go TLS＋Rust私有V3同签名Wintun实机产品双向与Stop PASS

H1743 SOURCE `17405b156f58e1f7b03ab781dafc2f6ad7e54a7e` [真实Windows/Ubuntu Action43414888803](https://github.com/lly8666/wbd-next/actions/runs/43414888803)，native-public-two-os job 131852507579 **SUCCESS**。同SOURCE构建原 Go EXE、原Rust release DLL（明确编入仅CI`m0_v4_probe`）、Ubuntu原服务端；签名 Npcap/Wintun 和独立 WSL2 内核真正启动。

- 特意使用`--route-mode all`，不是`bypass-lan`，以免Ubuntu TUN 10.66/24作为RFC1918地址被误当Direct路径：这次仅检验原 Go 登录凭据TLS＋Rust V3 native owner是否仍可真正把Windows↔Ubuntu应用UDP/TCP双向送过M3/原Rust，且原四阶段no-WFP WAL Applied/Stop能顺序退场。
- 原日志精确发出`PLAN029_H1743_REAL_ORIGINAL_GO_RUST_V3_TUNNEL_ONLY_SIGNED_STOP_PASS`、`WBD_WL_TRUE_PUBLIC_MODE_WIN_LINUX_DUPLEX_STOP_PASS normal`、`WL_PUBLIC_REAL_MODE_PROCESS_EXIT mode=normal rc=0 elapsed_seconds=10`、`WL_PUBLIC_REAL_MODE_RESULT normal PASS`。新断言还要求实机`WBD_PLAN029_V3_TRIAL_COLD_EFFECTIVE route_mode=all`、OS Applied、Stop无异常，以及原v2 WAL和routes sidecar均不存在，缺一不输出029 PASS。整Action非仅编译，另governance43414888888与维护43414888758成功。
- **结果严格为PASS_SCOPED_REAL_TUNNEL_ONLY，不是029完成**：未在此Action跑CN QNAME/IP并集、物理Direct UDP/TCP、两端DNS53、DNS TCP、精确owned Defender listener、GUI Ready、D1-D5/P1-P2、padding。不从legacy1400 Normal得出性能结论，不复活旧WFP或028矩阵。
- 下一步骤：把Rust已有的可选kernel TCP actor接入同代no-WFP synthetic /32+Defender rule精确WAL、按真实OS收据post-Apply授权；然后跑一场真正CN域名及IP并集与两DNS的signed Windows双出口应用级D1/D2，继续D3-D5/P1-P2和启动padding。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Record independently source-locked genuine signed Windows original Go TLS + Rust private V3 Tunnel-only two-way UDP/TCP and owned no-WFP OS Stop PASS; no Direct or DNS qualification inferred"}
```
