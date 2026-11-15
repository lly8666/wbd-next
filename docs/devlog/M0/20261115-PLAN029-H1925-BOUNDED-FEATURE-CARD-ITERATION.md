# PLAN029 H1925｜给功能卡留出写入余量，避免后续无意义治理红灯

- H1923功能卡 `dns-split-ipv6.json` 已达 **16370/16384 UTF-8字节**，剩14B余量。H1917/H1918曾因轻微增补历史描述超界而触发失败与补丁，浪费开发者和治理Actions轮次。H1925在不改变资格认定的前提下压缩16个冗长重复平台标签和7条历史中文/英文scope表述；本地校验**44条verification一条不删**，每条`status`、完整40hex`source_sha`、具体`evidence`路径一字不改。历史原始详尽说明仍在相应evidence/devlog中，本文件只做有界可读索引。
- 当前显示H1922 SOURCE `b0fa293733cbd56a4e5df6add8dc5b474cc7cb15` 的真实Win2025/WSL2 10GiB、500/700Mbps、SHA/FIN/11106个Tunnel UDP、双端Stop PASS，原 Go+Rust Direct 相对物理 CPU +12.281/+10.604s/GiB；P1/完整D1–D5/GUI/Game4/IPv6/padding仍开放。H1924廉价证据审计和治理已双PASS，不因功能卡简写提升产品资格。
- 本次仅docs/feature/cursor，**没有产品代码更改、没有触发新原生Windows/WSL2网络测试的理由**，不重跑已PASS的10GiB。
```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Bound 44 historical feature verification rows inside 16KiB while preserving every exact evidence path, source SHA and status; full PLAN029 still OPEN."}
```
