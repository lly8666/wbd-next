# PLAN029 H1728｜原Go冷配置进展与Windows GNU跨ABI真实首错

- H1727 `5de76fd79e4c07d798790a6e591a65de0e069e68` original Go Windows source compilation [43395331781](https://github.com/lly8666/wbd-next/actions/runs/43395331781) **SUCCESS_SCOPED**，不证明V3私有冷配置已在原产品调用，不证明真实DNS或双出口。
- 同SOURCE [r0-cross-abi 43395331794](https://github.com/lly8666/wbd-next/actions/runs/43395331794) Windows GNU job 131784753579 **FAIL**：MinGW Linux cross-link `ld: cannot find -lWs2_32`。只改原生Direct UDP/Direct TCP/原Rust actor三处 `#[link(name="ws2_32")]`；这是Windows DLL import lib 的大小写，Windows本地MSVC不敏感，Linux GNU区分大小写。
- 本变更不改变连接语义、物理NIC绑定、Defender、FakeIP DNS、MTU或性能。随同SOURCE自动触发跨ABI与Windows/Linux Rust/Go jobs，待实际绿灯再入证据。保留旧FAIL。
- 029正式 D1–D5/P1–P2、Normal/Game4双真实出口、DNS双方向、TCP、owned Stop、padding均**NOT_RUN**。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Repair real Windows GNU cross-ABI linker failure for native Direct UDP/TCP by canonical ws2_32 import; product networking unchanged"}
```
