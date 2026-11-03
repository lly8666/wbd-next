# H999｜收口后的目录大小格式修复

H998主线治理检查 PASS，功能目录检查因 `docs/features/entries/path-mtu-budget.json` UTF-8 文件大小超出 **16 KiB** 而 FAIL。H999只把**同一JSON对象**压缩为无缩进单行，严格保留所有27条verification、limitations、SOURCE证据和实验stage，文件实际UTF-8长度16033B ≤ 16384B；不修改产品代码、源锁原生测试、范围收口结论、registry 028 状态。检查完成后以新的GitHub governance Action为准。

```feature-impact
{"kind":"updated","ids":["path-mtu-budget"],"reason":"Only JSON whitespace compacted below 16KiB feature card size limit after H998 scoped PLAN027A closeout, same semantic entries retained."}
```
