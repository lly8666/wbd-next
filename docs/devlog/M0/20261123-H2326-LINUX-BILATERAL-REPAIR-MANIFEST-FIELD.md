# M0 H2326 · Linux 双原生客户端/服务端构件 manifest 读取兼容

- H2325 main Linux 18-case [45118015230](https://github.com/lly8666/wbd-next/actions/runs/45118015230) 的真实 Go 客户端、服务端、Rust/ISA-L 已编译，Rust 24+7 原生单元和三文件 SHA-256 都通过；本次运行在业务前读取旧 `manifest["source"]` 抛出 `KeyError: 'source'`，不是产品网络失败。
- 当前 `tools/arm64_public_go_rust_bundle.sh` 的真实 schema 是 `source_sha`，这次把 Workflow 2 处、Linux 原生案例 adapter 1 处改为同一字段。仍要求原生双方同 `GITHUB_SHA`、`architecture=x86_64`、三个文件 SHA256，各自 cold TLS、tc loss、Stop、CPU 原始证据。
- 12 个 Windows Game controller 已锁 `main HEAD 71e8304` 且正在依次分发，为防中途改 main 使其后续 `GITHUB_SHA` lease 失败，先在 **独立 Linux 测试分支 `experiment/m0-029-linux-bilateral-h2326`** 重跑 Linux 18 档。它的 source hash 与 main 不同，不得假称 main 18 档已过；只同步纯 Workflow 修正，不动产品字节。
- 本次更改只涉及测试基础设施，旧 M2 Receipt 仍废弃，外层 R 是表演外观，不是可靠交付；Game parity/首发 lane copy 不能归作 R。结果状态 `NOT_RUN`。

```feature-impact
{"kind":"updated","ids":["outer-opportunistic-repair"],"reason":"Source-locked test-only Linux Go client/server manifest field source_sha verified, without altering original product or repair budgets; 18 real bilateral scenarios still awaiting true native outcomes."}
```
