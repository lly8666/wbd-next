# PLAN029 H1958｜原 H1861 WSL ABBA 源码契约恢复（不假装网络通过）

- [H1957 Action43792440957](https://github.com/lly8666/wbd-next/actions/runs/43792440957) 真实 native-public-two-os **NOT_RUN**；原 cheap Action 的 36 个旧 H1749 用例仅 H1861 源源码保护失败：必须保留原来完整 `elif ABBA:` 和 `raise SystemExit("P2 ABBA requires explicit WSL argv, not env-only activation")`。H1957 曾把分支错误合并成 `elif ABBA or PRECON_BULK:`，功能逻辑接近但破坏受保护的源码契约。
- [H1957 governance Action43792441069](https://github.com/lly8666/wbd-next/actions/runs/43792441069) 两 job PASS，原 H1956 新 10项合成单测已通过，389条 1 cold+4 bulk+384 small 的构造已正确。勿删除或削弱原 H1861/H1849 测试。
- 本 SOURCE **仅** 恢复原 `elif ABBA:` 及原异常字符串，在其后添加**独立** `elif PRECON_BULK:` fail-closed；不改真实 Linux guest 原 ABBA 参数、不改 Windows Rust、Network Owner/Stop/MTU、正式 preconnect OFF。额外 H1956 source port +4x4MiB与384原 small 的新场景仍是唯一下一轮原 Windows/WSL2签名证据。
- H1955 的384/384 Windows 同机 QPC/真实4MiB/120 UDP/Stop仍唯一真 PASS 原生来源；H1956/H1957 原脚本/静态错误不能被写成任何性能结果，原 Actions 和证据保留。

```feature-impact
{"kind":"none","reason":"Restore legacy H1861 WSL ABBA source-contract branch and its exact fail-closed error while preserving separate signed-only H1956 preconnect bulk argv; no product/feature behavioral change."}
```
