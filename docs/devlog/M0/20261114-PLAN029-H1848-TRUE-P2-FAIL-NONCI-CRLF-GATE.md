# PLAN029 H1848｜真实P2否定单独回程FIFO性能假设；修Windows CRLF产品夹具并收紧feature字节界

- **真实负面证据一**：[H1844签名P2 Action43598740573](https://github.com/lly8666/wbd-next/actions/runs/43598740573) 源`ecd85c18` 的原Go/Rust+Windows2025 Npcap/Wintun和Ubuntu WSL2编译/OS完整实验已执行。普通物理1MiB=281ms，Direct连通750ms，上传1MiB=18703ms，半关闭到起始19453ms、首回包20860ms，36.657s收到918853B，38s超时；Linux完整收到1MiB+EOF并完成sendall；同时Tunnel UDP贯穿至少2432次。P2真实业务FAIL，场景Stop未合格。相比H1839上传18969ms，**只修H1843 TCP回程FIFO/环背压没有实质提速**。此SOURCE没有H1846“32条autoreset事件被合并”修复，不能据此否定后者。不得以组件编译通过或旧32KiB成功冒充本场1MiB性能达标。
- **真实负面证据二**：[H1845非CI正式产品 Action43599087343](https://github.com/lly8666/wbd-next/actions/runs/43599087343) 源`7e1d1259` 被新加`H1845 user CN source snapshot missing or changed`在原Go启动前拦住，**没有OS Applied/Ready/Stop或分流业务结果**。源中`rules.write_text("cn.example\\n",encoding="ascii")`在Windows把LF文本换成CRLF，随后夹具却`read_bytes()==b"cn.example\\n"`，错误地当作文件修改。H1848只用`read_text(encoding="ascii").splitlines()==["cn.example"]`验证唯一规则，仍保留原绝对拥有路径和`--split-enable`/无试验环境断言。此源只带一条`[plan029-real-product-cn]`新签名产品场景，不重派同一P2。
- **功能目录三**：H1847 [Feature catalog Action43600012717](https://github.com/lly8666/wbd-next/actions/runs/43600012717) 失败 `feature card must be bounded regular JSON`。此前只看JS字符长度，未按UTF-8中文**实际文件字节**计数，超过16KiB；H1848缩短摘要到16289字节以内，保留全部40+历史SOURCE的逐项验证，不改stage experimental，不篡改旧P2和D3的scoped通过记录。提交后功能目录仍以Action终态为准。
- 当前调度结构H1846单独真实Windows/Linux Rust组件[Action43599593131](https://github.com/lly8666/wbd-next/actions/runs/43599593131)均已PASS_BUILD；其Windows普通native回归另外运行。下一次真实P2应使用包含H1846的新SOURCE并对照H1844同VM测试；不在本H1848产品marker混场。
- Game4 CN、IPv6 no-old-WFP、GUI原按钮/OS Stop、慢磁盘FakeIP持久化压力、纯Tunnel P1 CPU仍OPEN。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Bound 16KiB UTF-8 feature summary to actual H1844 P2 failure, H1846 unqualified scheduler fix, H1845 Windows newline fixture failure; rerun independent explicit non-CI signed product only."}
```
