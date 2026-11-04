# PLAN028 H1105 x86 Game4 overlap 复验 / H1106 ARM64 Fixed 冻结任务

[Action 41790304416](https://github.com/lly8666/wbd-next/actions/runs/41790304416) SUCCESS。独立下载工件13303345412，与旧构建产物13299199278的SOURCE0e47 manifest/ELF SHA完全相同，无重建。x86/x86 真实Go TLS/Rust Game4 fixed6、同一443：OS物理源IP.2→.3，新组READY先于旧组Stop，FEC6 parity两代真实发生，受保护租约不变，旧/新5+5 UDP、MTU1178读回；真实Server TCP重组看见8条ClientHello，每代4条，Server没有提前私有payload，SessionID各32B且8个不同。旧 [Action 41782228876](https://github.com/lly8666/wbd-next/actions/runs/41782228876) 仍为FAIL（EIGHT/8门禁拼写），新Action才是本限定场景PASS。详见 `docs/evidence/M0/PLAN028-H1105-SOURCE0E47-X86-GAME4-OVERLAP-8CH-20261104.json`。完整 TLS Finished/同uTLS基线另见H1095，不从首飞pcap推断。

下一Linux任务遵照用户交替为原生ARM64 client+ARM64 server：新 `m0-plan028-arm64-fec-fixed-source-frozen.yml` 下载 H1104 真实ARM64源码32cd已建的Go/Rust ELF二进制，不编第二套；只测 Normal Fixed1 同样的源IPv4/物理MTU新路径，旧64、新5 UDP、/32/内层OS和精确Stop，异构QEMU矩阵不重开。新Action结果未收前为PENDING。

保留H998旧在线同连接MTU收窄FAIL、ARM64 Game4FEC旧Action FAIL、Windows物理NIC/CPU/p99及远端ICMP未测。

```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient"],"reason":"H1105 original x86 Game4 FEC6 8 real TLS ClientHello, A→A+B→B genuine UDP/MTU/Stop PASS; H1106 native ARM64 fixed-source frozen path trial pending."}
```
