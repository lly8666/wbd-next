# PLAN029 H1767｜首个签名外层全绿后验证DNS无回退；并行扩原M1 padding接入点

- [H1766签名Action43524162967](https://github.com/lly8666/wbd-next/actions/runs/43524162967) **SUCCESS**，源码 `c6bff330b237d59b2aff2b5c96aa62725d666a38`；[真实原始归档14084433794](https://github.com/lly8666/wbd-next/actions/runs/43524162967/artifacts/14084433794)。Windows2025签名原Go TLS/Rust/Wintun+Linux原TUN，同会话的中国域名FakeIP/真实物理Direct UDP与32KiB TCP+FIN、非中国Tunnel TCP/UDP、非CN `www.globalx.example` 应用查询原呈现`8.8.8.8`经唯一Tunnel`1.1.1.1`收到/回原DNS源、原双OS Stop与Defender/HyperV精确清理均通过；独立严格029外层准入也打印 `PLAN029_H1766_OUTER_SOURCE_LOCKED_DIRECT_TUNNEL_DNS_TCP_UDP_AND_STOP_PASS_SCOPED`。这是029单Normal真实范围PASS，不是D1–D5/P1–P2最终结束。
- 新H1767在**这同一已有签名场景**完成上述正向DNS后，保持当前owned Linux TUN 1.1.1.1/32，独立Linux双socket分别监听Tunnel`1.1.1.1:53`不回应、物理`peer:53`作Direct逃逸哨兵；Windows真Wintun应用三次查询另一个非CN域名`no-backup.globalx.example`，要求Linux Tunnel收到至少2次、物理收到**0次**、Windows在测试窗口无响应；Linux观测覆盖原native DNS约5s预算。反例即FAIL，不用假系统DNS、fakeip或第二个解析器。测试专用进程仍由原owner `finally` 收回，H1765的精确/32所有权回收未更改。应用TCP53、同endpoint UDP-TC→TCP等仍NOT_RUN。
- 资源线增加129项关闭TCP NAT元数据/每tick最多64项到期的纯测试，延续H1766的旧TX timer最早到期唤醒，不新建线程或10ms忙轮询。
- Padding并行新增**原M1 LINK AEAD的可选0–256B扩展入口和FrozenRecord PN/Seq长度一致性单测**；严守老codec inner marker+AEAD、原始packet不修改、无第二PN allocator/密文重传重新seal。尚无冷配置/分类器真实Tunnel-only调用、GUI effective/MTU/off-on/CPU-p99实测，必须继续标不完整。
- 只发一个H1767当前SOURCE/Normal签名Action，先Cheap/Windows/Linux Rust/Go验证，再真实双出口/新DNS反例/Stop。保持028限定收口、030不开工。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6","startup-flow-padding"],"reason":"H1766 signed real Direct/Tunnel and strict outer gate scoped PASS; H1767 DNS one-upstream blackhole negative and authenticated M1 padding adapter are source pending"}
```
