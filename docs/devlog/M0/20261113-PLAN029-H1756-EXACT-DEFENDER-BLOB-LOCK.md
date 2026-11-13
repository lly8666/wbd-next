# PLAN029 H1756｜原始装配SOURCE锁首错修复

- H1755 SOURCE `61dd065515cc8ea19f6e536b5b96a581059c9857` [Windows43440493323](https://github.com/lly8666/wbd-next/actions/runs/43440493323) 首错是 `prepare_windows_wiring.py` 的 `assembly blob mismatch: ...native_plan029_defender_com_windows.go`，**Go与Defender均SKIPPED/NOT_RUN**；另三个同源自动工作流43440493321/43440493098/43440493004 FAIL，未证明新的网络故障。
- Git blob读回为 `5dee93798090774adad82bd21280bdcf0c489565`，旧manifest记录 `00a504ab046da5d2e0fe1588b454e548058e4c0b`。H1756仅同步已变的该文件 `result_blob`，不删除或绕过校验、不修改原Go绑定源、不重复dispatch。
- H1754 real COM单规则Add/readback+Cleanup FAIL和WAL保留原样；H1755的首字段观测代码尚未得到实机结果。收 H1756 后继续定向定位，不宣布Ready。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"H1755 source assembly expected blob mismatch recorded; H1756 exact manifest COM hash update, native COM remains NOT_RUN for new source"}
```
