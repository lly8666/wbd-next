# PLAN029 H1735｜H1734 Windows DNS首错（测试读取偏移）定向修正

- H1734 SOURCE `0d5158a0823e92f3a63ab8c8bb0a1e2e6ded0b0d` [Action43402459789](https://github.com/lly8666/wbd-next/actions/runs/43402459789) Windows2025 Rust **54 PASS/1 FAIL**，仅旧DNS回注测试：期望RFC1035 SERVFAIL的RCODE=2却错读回包byte29，此处是DNS transaction ID；实际flags byte1位于IPv420+UDP8+DNS偏移3，即byte31。改`reply[31]&15`，不修改正式代码、实际socket、MAC或TLS。
- 新的Tunnel DNS 2条用例已经通过，原Go/Rust V3 ABI先前PASS；本SOURCE cross ABI [43402460051](https://github.com/lly8666/wbd-next/actions/runs/43402460051) 和治理 [43402460095](https://github.com/lly8666/wbd-next/actions/runs/43402460095) PASS_SCOPED。保留旧Action原FAIL证据，不再重复此前诊断。
- 新SOURCE Windows/Linux Rust 029自动定向回归待结果；正式Rust/Go四阶段产品、Direct kernel TCP、DNS TCP截断同端点、owned Defender+Stop、D1–D5/P1–P2和padding仍**NOT_RUN**。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Correct exact DNS SERVFAIL wire test RCODE offset while retaining first H1734 Windows scoped test failure; production behavior unchanged"}
```
