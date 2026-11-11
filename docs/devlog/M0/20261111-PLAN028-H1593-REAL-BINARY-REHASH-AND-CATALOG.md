# PLAN028 M0 H1593｜源锁全平台构件实体重哈希与功能卡纠偏

PLAN028 **IN_PROGRESS**。基于本源 `fd4732ec4adffa442a0bc25a145ed6ea1d1259a8` Action `43009320538` 下载原始 Windows build ZIP `13850805988`，Linux x86 原始 build ZIP `13849279449`；直接读取 exe/DLL/Go client/server/Rust so **字节重算SHA256**，全部与单文件manifest相符。补读 Action `43009320436` ARM64 native真实内核TLS/TUN两账号/59 UDP/owned Stop收据与 `43009320564` ARM64 ISA-L静态加速11-source build SHA256SUMS，**两份ZIP均不带ARM64二进制，不能宣称本地复算或NEON运行时通过**。四组精确文件hash和后端见 `docs/testing/PLAN028_M0_ACCEPTANCE_COVERAGE.md` H1593表。

额外在本地运行上述 Linux x86_64正式 `wbd-v4-client --help`（退出码1表示Go flag请求帮助），复核 Normal/MTU1460/ChaCha/机会重传on/Game-FEC off/轮换默认0；固定FEC profile默认数值1不等于FEC模式自动on。Windows真实 `fd4732ec` OS原日志显示15/90/idle0、原始TLS、Wintun inner1389及手动/32。当前正式产品默认与测试专用显式开关不混。

同时更正过期 `docs/features/entries/windows-native-transport.json` 的旧M4开发分支为 `main` + M0、H1590未验为H1592真实冷建链scoped PASS，增加H1587双Windows路由抢占FAIL、限制和原始证据。保持卡stage experimental：有真实正向不等于全028硬门完成。修覆盖表顶部旧813接线误当最新源码和已成真的Windows自动AES256旧SOURCE，仍明确保留当前SOURCE差异与新源150s在途。

新SOURCE `8c0421c3` H1581独立 Windows自动AES256+四Linux三套AEAD 150s `43014043726` 在途；**绝不在本H1593构建/文档更改里重新派发网络场景**（commit marker `[plan028-harness-offline-only]`）。原 H1587 FAIL、L2/最终L3/物理公网/Android NOT_RUN不改判。治理基线 `2c59b975` Action `43014262368` feature/governance均SUCCESS；原8c治理失败保留。

```feature-impact
{"kind":"updated","ids":["windows-native-transport"],"reason":"Corrected live M0/main ownership, source-locked 30pct scoped success and still-failing dual-Windows owner; no changed product behavior or default; old evidence retained."}
```

治理跟进：H1593卡首次长度超上限，按UTF‑8 16384字节限制收紧重复的卡片历史描述并继续保留旧devlog；单独更新卡片时未在同提交提供带`kind:updated, ids:[windows-native-transport]`的devlog审计声明。现同提交更正两项；原FAIL不删除。
