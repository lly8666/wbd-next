# PLAN029 H1710｜真实Win内核TCP完整DATA/FIN PASS；CN FakeIP持久租约源代码

- H1709 [Action43361106714](https://github.com/lly8666/wbd-next/actions/runs/43361106714) SOURCE `ac292b0530659647da522e79fd2381995ed1c250` **真实签名Wintun隔离诊断PASS**。Windows真实应用SYN→Rust SYN NAT→本机内核SYNACK/Accept→绑定真实物理源和ifindex的Rust TCP→独立Ubuntu WSL2 Linux内核；两腿EOF后Rust继续唯一Wintun RX读取并逆向提交真实内核TCP FIN，Windows原应用读完实际应答且正常EOF。上一H1708没有FIN导致15s超时FAIL保留。Host HyperV仅一个owned guest TCP Allow，Action Cleanup成功。此为显式m0_v4_probe，非TLS/Normal/Game4正式product Ready；WSL2异内核/同Windows宿主vEthernet，不是公网物理机器。
- 同SOURCE Rust eligible library Windows317、Linux292全部PASS，其中新 `v4_client_dns_answer.rs` / `v4_client_dns_pending.rs` 8项CNAME多A/共享CDN additional隔离、NXDOMAIN/TC、原query ID/QNAME/resolver/lane及256级合并/超时/同endpoint TC→TCP纯单测PASS；仍无实际DNS socket。
- 新 `v4_client_fake_pool.rs` 单Rust worker拥有的CN FakeIP映射：原始QNAME+canonical CNAME+真实A+policy/resolver版本共同key，返回本地fake不做realCDN反查；每条60s合成TTL上限，TTL0仍10min隔离，flow ref保护不重绑，Fake容量/字节单独限制、过期按BTree到期索引有限预算回收，不每包全扫。
- 分配先 `prepare`，源冻结持久portable snapshot的真实Writer拿到存储完成回执后才能 `acknowledge_durable` 并把Fake放入DNS答复；未经真实持久化不可冒充Announced，重启恢复隔离映射，容量满只局部拒新Fake不走隧道、不污染现有表。本次只是**待SOURCE测试的纯租约/序列化数据模型**，不含真实文件原子写/GUI/解析查询/真实Wintun封装。下一道先做Rust单测后装正式owner的物理/隧道DNS网络与D1-D3，保留历史失败。
- 不恢复旧WFP、Go逐包、无认证私有TLS前导，不重跑028矩阵/030。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6","windows-native-transport"],"reason":"Collect true H1709 Windows application kernel TCP reverse FIN/EOF PASS and DNS parser/coalescer cross-platform tests; stage single-owner selective FakeIP durable/quarantine/ref source without fake product readiness."}
```
