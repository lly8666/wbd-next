# PLAN029 H1847｜按真实SOURCE修正功能目录

- H1846 `715a5dd0be89c8fb2786f515912ceb005ffcf3d8` 自动复位事件满32条就绪重查修复后，[治理Action43599593084](https://github.com/lly8666/wbd-next/actions/runs/43599593084) 结构PASS，但Feature catalog因`feature-impact kind=updated`未同步`dns-split-ipv6`卡而FAIL。H1847只更新真实功能卡摘要，保留experimental Stage、旧SOURCE验证/evidence记录不变。
- 独立真实事实：H1838真WinForms→原Go配置读回PASS；H1839 SOURCEa50签名P2普通物理1MiB297ms vs Direct上传18.969s，38s未收完整回显、Rust回程积压64KiB，性能FAIL。H1843改了TCP反向Mailbox/Wintun满时有界FIFO，H1846改32/32有限工作误睡眠，**源码已修并不等于新实网性能证明**。
- [H1844签名P2 Action43598740573](https://github.com/lly8666/wbd-next/actions/runs/43598740573)、[H1845真实用户显式CN签名产品 Action43599087343](https://github.com/lly8666/wbd-next/actions/runs/43599087343)、[H1846源码回归 Action43599593225](https://github.com/lly8666/wbd-next/actions/runs/43599593225) 独立在测。此提交不含签名scene marker，不重新派网络，Stop/吞吐均待各SOURCE真实终态。Game4 CN/IPv6、GUI真OS Stop、FakeIP慢日志压力、P1 CPU仍OPEN。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Synchronize feature inventory with H1839 signed P2 performance failure and H1843/H1846 Direct source fixes without claiming unrun product or P2 PASS."}
```
