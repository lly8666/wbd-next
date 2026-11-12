# PLAN029 H1678｜功能卡状态 schema 兼容修复

- SOURCE `44beaa61cdbe3a1125ab707f5591b6fc20a76085` governance Action [43223029446](https://github.com/lly8666/wbd-next/actions/runs/43223029446): M0 role/scope SUCCESS, feature catalog FAIL on `dns-split-ipv6: unknown verification status`. This is because H1677 added `UNIT_PASS_ONLY`, which isn't a canonical feature status.
- Existing catalog allowed `BUILD_PASS` is used with original source-locked scope explicitly **pure compiled Rust 5 unit tests only**, not DNS/Direct product functional/physical PASS. No source/test data changes; tests remain at SOURCE `a5ef2cd0108946e380599895558b377f8686a208`.
- Keep previous H1676/H1677 failures in Actions history; do not upgrade core D1–D5/P1–P2 or hide H1672 signed Windows native TCP no-SYNACK.
```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"H1677 feature inventory schema rejects UNIT_PASS_ONLY; normalize to BUILD_PASS explicitly pure Rust unit-only, preserve source and network NOT_RUN."}
```
