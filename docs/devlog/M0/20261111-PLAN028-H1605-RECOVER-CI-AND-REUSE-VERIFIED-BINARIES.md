# PLAN028 M0 H1605｜CI外部DNS故障停止原生网测后，复用已核实产品构件

### 原始失败
`43034982111`（SOURCE e17a）、`43035399302`（SOURCE d84b）、`43035735021`（SOURCE 09ea）**全部Actions失败**：原Linux编译任务在 `sudo apt-get install ... nasm ...` 时对 `azure.archive.ubuntu.com` 解析失败，退出码100。Windows真实近内层MTU原生Job均SKIPPED，**没有真实MTU/产品业务收据**，不得计为产品FAIL或PASS。H1604治理`43036467255`失败是cursor `context_refs=9` 超策略 max8；本提交限至8，历史证据保留其他文件引用。H1603旧单测变量拼写已修、治理回归`43035735075`成功。以上原Actions不删除。

### 仅在H1602使用已经构建并重算的标准产物
原证 SOURCE `8a31375e36bb6a93860c5579e64b4a39d0b6e346` Action `43027983611` **整体SUCCESS**，Windows正式二进制artifact`13859392613`，Linux x86_64正式artifact`13860905669`；本地逐文件重新hash并与原CI manifest匹配：Windows `wbd-client-embedded.exe=63b4a24abb0e7c775be5e58d3e54036f4bfab0491bc992a0147b8fe57886cd7c`、`wbd_engine.dll=7c8ddd808d08cfa18cf431fd5945d6c705bddaa6dd19a94e1891170ffa91d37d`；Linux client`7f347ae9dc878edf508aa5fdeb8668ccae653682d01898435b69d42c94a555d1`、server`9188f3941eba3dfd48831f779e0d8b73d3b31deda4c1978a1f270e11d75dcc71`、Rust so`2947d148d325e198acd920c56803ad168175ba11590396478682693fcf5922dc`。所有正式构建ISA-L静态native加速，非scal​​ar fallback。GitHub compare `8a31375e..1289fd8` 5提交只更改测试/CI/文档，`crates/`、`r0/go_overlay/`、Cargo/prepare_windows_wiring无产品diff。

本次只为`[plan028-h1602-near-mtu-five-native]`在原workflow复用上述现成原Go/Rust产物，先核历史Action与SOURCE、`git diff`产品路径零改、实际二进制hash/ISA-L启用，再进入一个真Windows签名Wintun＋四Linux TUN短网测。精确区分当前测试harness SOURCE（新SHA）与原产品二进制SOURCE（8a313）；其他普通正式构建流程不改。原用户默认outer1460、内层只OS读回；不会修改产品、GUI、协议或FEC默认。旧H1600 150s同账号原场不重跑。

本提交只派发 **一个** 真实近MTU场景，必须以原始strict报告确认20次内层MTU-1/MTU真实双向内核UDP原字节回声、Bob延续及六owner Stop，之前仍为NOT_RUN。不运行多Wintun，保留H1587历史路由归属FAIL限制。

```feature-impact
{"kind":"none","reason":"Only test-scoped verified original binary reuse and governance cursor fix, no product feature or default change."}
```
