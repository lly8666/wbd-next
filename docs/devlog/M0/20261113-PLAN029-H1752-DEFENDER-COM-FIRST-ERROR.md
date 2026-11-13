# PLAN029 H1752｜真实Windows Defender COM编译首错的精确定向修复

- H1751 SOURCE `47317155df4d678cc9698cce62b4feec47d40066` [Windows Go Action43435540007](https://github.com/lly8666/wbd-next/actions/runs/43435540007) **FAIL**。首错：原生`INetFwRule` COM wrapper 在第133、190行使用`k.Local4`，但账本`n4Plan029DefenderKey`的规范字段是`Lease4`。保留原日志与SOURCE，不能把编译FAIL记作产品联通失败。
- 只改这两处为`k.Lease4`，保留原生COM/sidecar的接口、规则方向、唯一端口和代际归属，更新当前`manifest-plan020-m0.json`该新增源码的`result_blob`；不动历史冻结PIN或旧WFP。
- 新Windows Go同SOURCE的编译、`TestPlan029Defender*`故障注入测试自动由H1661触发；结果收到前PENDING。
- H1750签名 CN DNS→FakeIP→Direct UDP和Tunnel TCP/UDP+受控Stop真实PASS_SCOPED；完整原生Direct TCP post-Apply Defender/Stop、D1–D5/P1–P2、padding与GUI仍NOT_RUN。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Fix first Windows COM compile error k.Local4 vs canonical Lease4 and repin only live overlay assembly blob; preserve H1751 failure evidence"}
```
