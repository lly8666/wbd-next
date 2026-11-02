# PLAN027A H977｜源锁的两处测试替换改成逐行唯一锚点

H975 [41484325423](https://github.com/lly8666/wbd-next/actions/runs/41484325423) 两端Rust/Windows原Go预检PASS，Linux已成功安装7个FakeTCP产品文件，但新测试-only安装器发现`wire_qualification_test.go`内有两处`DefaultMSS`，原脚本拿不带上下文词判断“必须1处”，因此正确拒绝覆盖。先向固定上游 `lly8666/wobuzhidao@a7a82db...` 读取两个原始完整文件，与当前overlay逐字比较：TLS测试只有一处改变，Wire测试正好两处改变，三条**完整行/上下文锚点**各出现恰好一次，处理后内容与manifest result blob完全一致。因此H977仅修这些定位词，绝不放宽原Git SHA+全文一致校验、不碰任何产品Go/Rust。之前每次失败保留，后续构建/原生另看Action结果。

```feature-impact
{"kind":"none","ids":[],"reason":"Tighten test-only Realityfront MSS source replacement to three unique exact original Go line contexts, preserving immutable source and product code."}
```
