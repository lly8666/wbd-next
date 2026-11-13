# PLAN029 H1747｜Windows签名原生场景触发器遗漏定向修复

- H1745 [Action43422444895](https://github.com/lly8666/wbd-next/actions/runs/43422444895) 真实签名Windows/WSL2原Go Rust V3、CN物理DNS/FakeIP Direct UDP与非CN Tunnel still IN_PROGRESS；Cheap/Win+Linux Rust/Go/Lin产物编译均SUCCESS，不等于实际业务。
- H1746 SOURCE `ace4f60f5a46e595b79f3324182346cd0201592e` 把旧Windows**测试专用**Defender TCP45902 RemoteAddress从10.66.0.1精确改为本场Linux非CN owned TUN别名203.0.113.77，readback/按run名称Stop删规则不变。H1746 治理 [43423895675](https://github.com/lly8666/wbd-next/actions/runs/43423895675)及维护43423895601 SUCCESS；但原Windows实网worklow的`on.push.paths`未含自身YML且提交未触及其它触发源码，**没有签名 native Action**，不得冒称结果。
- 本批只补将`.github/workflows/m0-wl-public-normal-full.yml`纳入自己的push路径，并加原scope单测：workflow文件改动无显式marker只做cheap，使用`[plan029-v3-real-direct-udp]`才执行这一场Windows/WSL2签名场景。不扩大常态七模式或旧028矩阵。H1747结果待同SOURCE实跑。
- 完整PLAN029后续仍欠真正Direct TCP product Defender、独立Tunnel DNS证据、D1–D5/P1–P2和padding。H1743只有Tunnel-only已真实PASS。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Repair signed native workflow self path trigger and prove new H1747 CN Direct UDP real source only runs with explicit marker; H1746 had no actual network Action"}
```
