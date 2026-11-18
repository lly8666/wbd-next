# H2193｜PLAN029 Linux Normal/off 填充接续（候选，未测）
  
恢复H2177–H2188的真实SOURCE与Linux原客户端/服务端调用链；H2186 `e174235872d32cca69bf921fb59904f9bcaee889` [Action44278039887](https://github.com/lly8666/wbd-next/actions/runs/44278039887) 原生x86_64/aarch64各8场16/16 PASS_SCOPED，不重复老矩阵。只增补 Normal/off `--startup-padding tls|flows` 两场/ISA。原Go认证/Detach→native Rust entry cold setter→同M1凭据owner+AEAD/PN LINK seal→M4 AF_PACKET raw syscall，`off`不建跟踪表；只以原始raw内核copied PN前缀累计填充，MTU房间、256流上限、2–3s/20–30record原Rust算法不改。无Go逐包回调、无新外层wire；Linux Fixed/Auto严格拒绝，不能把kind2/3改写为kind1。原Game off/tls/flows功能保持。

夹具仅在新增`NORMAL_PAD_ONLY`标记下运行2个Normal场景，双端真实TCP/UDP和owned Stop，每ISA一原SOURCE构建，成品SHA manifest核对；旧8场受控保留、不重跑。当前仍是 **CODE_CANDIDATE/NOT_RUN**，真实原生Linux结果只能从之后Action核验，不把源码存在写成PASS。

旧 Linux 无离线route-key 时 X25519 入口在H2185主动拒绝，符合当前TLS契约禁止ClientHello前私有前导；不恢复旧前导。Linux auto-IP物理实时1500→1280重认证独立NOT_RUN（旧manual动态fixture不足），实体ARM板、跨ISA物理互联、完整应用TLS与CPU/p99独立NOT_RUN。完整029/029B技术出口OPEN、030不启动。

```feature-impact
{"kind":"updated","ids":["startup-flow-padding","linux-raw-tun"],"reason":"H2193 Linux Normal/off original authenticated Rust LINK cold padding candidate; pending dual-ISA real native evidence; no historical qualification promotion"}
```
