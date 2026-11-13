# PLAN029 H1708｜H1707真Windows TCP握手/物理连客体PASS，Relay首次IO失败

[H1707 Action43358618332](https://github.com/lly8666/wbd-next/actions/runs/43358618332) SOURCE1165：真实Windows app SYN经签名Wintun Rust NAT32768→内核SYNACK逆写回app→本机内核Accept synthetic198.19.87.99:32768→Rust物理绑定172.22.160.1 ifindex22连接独立Linux guest172.22.166.190:46099 **均真实PASS**。随后第一轮TcpDirectRelay 返回generic RelayIo；app read超时、未得到远端TCP payload/半关闭，不算TCP端到端PASS。精确owned WSL Hyper-V TCP rule删除成功。

本批只修复非阻塞WinSock connect状态判定：等待WSAPoll POLLWRNORM再核SO_ERROR和真实peer，不能仅peer_addr成功认连接；操作只发生pending connect，不进入普通DATA。同时把泛化RelayIo改成准确inner/outer读写/半关闭stage及WinSock原码。下一Action复用原单场景，先读首错，不更改WFP/系统防火墙/普通Tunnel/新大重传。新SOURCE未验。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6","windows-native-transport"],"reason":"Preserve exact H1707 real TCP SYNACK/Accept and physical Linux connect positives plus first relay FAIL; source change WSAPoll completion and exact per-leg OS errno."}
```
