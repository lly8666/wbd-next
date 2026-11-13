# PLAN029 H1765｜H1764真双出口/Stop全过，但夹具finally遮蔽Popen

- [H1764 Action43511857343](https://github.com/lly8666/wbd-next/actions/runs/43511857343) / [产物14078389727](https://github.com/lly8666/wbd-next/actions/runs/43511857343/artifacts/14078389727)（SOURCE `7ad30db2454837a4f9276bf5b47cbc37ef58bf63`）：签名Windows/Wintun+原Go TLS/Rust/Linux TUN里真实CN CNAME/FakeIP Direct DNS/UDP、物理TCP32,768字节回显与双FIN、非CN Windows→Linux Tunnel TCP及双向UDP、当前代 Defender/WAL和双OS owned Stop依次打印PASS。属于单场景的实际业务证明，不是D1–D5/P1–P2全项或性能证明。
- Action最终 **FAIL** 的第一个新异常在业务及Stop后：Python `tools/m0_wl_public_normal_e2e.py` 的TCP证据 `wa,li=json.loads(...)` 遮蔽最初Windows真实UDP `Popen wa`，`finally` 里调用`wa.poll()`出现 `AttributeError: 'dict' object has no attribute 'poll'`。H1765改为 `tcp_windows_receipt` 和回归单测，不覆盖历史失败、不放宽原owned清理。
- 并行增加最小真实D1反例：同一原始签名Wintun/TUN下Linux先建立**当前SOURCE owned** `1.1.1.1/32` 原TUN UDP53 listener，Windows应用绑定 `10.66.0.2` 发非CN `www.globalx.example` 到任意呈现DNS `8.8.8.8:53`，要求Linux只在唯一Tunnel端点 `1.1.1.1:53` 收到QNAME及Windows原源，并回签非Fake A，Windows客户端收到原 `8.8.8.8` source。记录intent→OS Applied→readback和finally精确删除；无新公共放行/旧WFP。上游同endpoint TCP回退、客户端TCP53、黑洞无fallback尚NOT_RUN。
- 当前H1765新SOURCE仅一Action一Normal网络场景，先原双出口后Tunnel DNS，再Stop，失败保存双方日志及第一边界。028收口不重跑、030不开工。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Preserve H1764 scoped real dual-egress+Stop PASS but harness FAIL; H1765 corrects finally shadow and adds nonCN Tunnel DNS actual OS fixture"}
```
