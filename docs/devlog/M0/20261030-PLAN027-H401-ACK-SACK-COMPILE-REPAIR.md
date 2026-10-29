# PLAN027 H401｜修复 H400 真实编译首错
2026-10-30。回收 [H400 native40945968960](https://github.com/lly8666/wbd-next/actions/runs/40945968960) build FAIL（verify skipped）；同源码 [r0-fake-platform40945968858](https://github.com/lly8666/wbd-next/actions/runs/40945968858) 编译 stderr 给出两个确切首错：
- `ipv4_tcp.rs:297` `as u8<<4` 被 Rust 解析为泛型参数起始，改为括号包围 cast 后移位。
- `ipv4_tcp.rs:292` IP checksum 与目标 `ip[10..12]` 同一表达式导致 E0502，按原 ACK builder 先计算 checksum 局部变量，再写入。
无协议行为变化，保留 H400 失败；main push 新 SOURCE 自动编译验证。H400 governance40945968922 PASS，其他因相同源码编译失败的 Actions 不视为功能 FAIL 通过。PLAN027 线上 Receipt 退役和 A/B/C 仍未完成。

```feature-impact
{"kind":"none","reason":"Compiler-only correction of H400 cast precedence and checksum borrow; no additional product feature or parameter semantics."}
```
