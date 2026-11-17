# H2134｜Game4 高级 CN 四 lane 真原生验收 PASS_SCOPED

SOURCE `5fc22aef30aa4440e81257e67fded501fece3080`，[Action 44197717052](https://github.com/lly8666/wbd-next/actions/runs/44197717052) **全SUCCESS**。原ZIP `14380098426` SHA256 `fba228b2e3b14a30863ce057a083bfcab268de79472eb6853e80f7a3e2dd2842`、27成员CRC PASS，产品EXE/DLL/Linux服务端均源锁。原Windows TLS/Npcap/Wintun/Rust四个 Game4 lane（FEC off）与 WSL2 Linux TUN 四个真实会话，外层MTU **1400（非1460默认）**；显式 `--cn-domain-direct=true`，真物理DNS53→FakeIP `198.18.0.1`，原两端Direct UDP回执、物理Direct TCP 32768B + half-close PASS，Tunnel 双向 TCP/UDP 真kernel PASS；原Win Rust join/WAL+LinuxTUN owned Stop PASS。完整 mode-batch PASS。
唯一短段真实进程CPU `0.4688 CPU-s/9.156 s`、PeakRSS `61,652,992 B`，不能当 B5 同VM 10Mbps A/B、每实际GiB成本或p99证据。Game2 `split-enable=true` 源码明确提前拒绝，**不是实际业务 Game2 PASS**。Game4默认1460/Fixed FEC/普通CN/all另保留NOT_RUN，029B仍OPEN；独立B4原生Action仍在途，不重新派发。

```feature-impact
{"kind":"none","ids":[],"reason":"Only archive signed original Game4 advanced CN native evidence; no runtime/product edit."}
```
