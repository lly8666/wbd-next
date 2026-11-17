# PLAN029 H2046｜功能卡严格UTF8限额

- H2044 feature catalog失败是单卡UTF8 16759B超过16384B，而非产品网络。保留全部已有verification行及其FAIL/NOT_RUN/实际evidence链接，仅压缩重复平台名称和当前摘要，并移除2条可从现有devlog追索的冗余源码引用；本卡16325B。
- [H2044 Windows源码/Go测试Action43992993306](https://github.com/lly8666/wbd-next/actions/runs/43992993306)SUCCESS仅BUILD_PASS。H2045签名WinForms→原Go/Rust网络与Stop另行实测，仍在途。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Preserve all historical verification statuses and evidence while restoring 16KiB UTF8 card budget."}
```
