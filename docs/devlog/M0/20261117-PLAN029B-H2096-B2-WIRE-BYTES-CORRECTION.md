# PLAN029B H2096｜真实DNS ticket仅修测试字面量，不重复正在运行的签名场景

回读 H2095 SOURCE `aa53d4b3b73d57d993f5bb0da1f29e8cc54462ef` 后发现工具代码中 `b"\\\\x62\\\\x02"` 是**错误的两层反斜杠**，实际 Python byte 串是ASCII文本而不是DNS事务ID `0x6202`；同段 `b"\\\\x01\\\\x00\\\\x00\\\\x01"` 也错误。工具构造提交时漏做 `ast.parse` 语义验证。H2096仅把这两处还原为单层源码转义，并加Python AST取真实byte constant的精准单测，不扩展为新DNS框架、不改Windows/Rust产品。

SOURCE `aa53d4b3...` 的 [Action44074535313](https://github.com/lly8666/wbd-next/actions/runs/44074535313) 已启动，**本记录时仍在途；不取消、不在本次提交重复标记同一真实场景**。H2096新源码仅有冷静态修正，物理验收记NOT_RUN；原真实H2093/H2094 PASS_PRE_STOP及FAIL原证保留。前述 H2094 的系统背景 A 查询属于Tunnel DNS正确出口，但原夹具未按test-id区分，H2095合理场景范围未变。下一步仅按原Action结论择机复验后续TCP45902与Stop，防止假PASS。

```feature-impact
{"kind":"none","ids":[],"reason":"H2096 exact Python signed B2 fixture wire bytes/AST test only; no product code or scene dispatch"}
```
