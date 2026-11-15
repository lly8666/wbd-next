# PLAN029 H1874｜治理与功能卡收尾，不改029 Rust SOURCE

- H1870 [Windows Rust原组件Action43660216474](https://github.com/lly8666/wbd-next/actions/runs/43660216474) 首失败是原单测 `assert!(n>=40)` 无法比较新增枚举，H1872只修改旧单测期待结构，H1872新Win/WSL签名P2尚在途，不能把native-functional纯测试绿当实网通过。
- H1871 feature卡超过16KiB、cursor refs超8的错误已经按实际阈值修；H1872 Governance结构失配来自新聚合证据混合SOURCE，本cursor只引用匹配 `eccafcd7` 的H1869真实IPv6限域证据，H1867/H1868异源事实仅保留在H1870聚合归档与devlog。H1873 [Governance Action43660700731](https://github.com/lly8666/wbd-next/actions/runs/43660700731) 结构PASS但Feature catalog失败，原因是本批更新功能卡却未在**同一提交改动**的devlog声明；H1874补此精确归属声明。
- 本次无代码/网络/防火墙/GUI变更、无再dispatch。真实P1 +9.41% CPU/GiB仍OPEN；Direct hard8与两出口限域PASS、真实IPv6/socket/Game4/GUI/剩余资源满场景均如实未齐。性能改进尚未定量成立。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"H1874 closes exact change-scoped feature catalog declaration after correcting cursor provenance and 16KiB feature-card budget. Product source remains H1872."}
```
