# PLAN027A H969｜先真实Normal1460再并行复用七个最小MSS模式

H968 Windows Go生产和Go实际SYN字节测试已PASS，Windows/Linux Rust单元测试PASS，唯一H968 Windows/Linux源码编译Action [41480121662](https://github.com/lly8666/wbd-next/actions/runs/41480121662) 正在最终Linux Go/Rust原生构建中。此H969一键工作流**绝不编译产品**，先要求该Action完整SUCCESS、原始SHA `0645b22ea852b80075a2227f472802bc76acf499` 和两个经实测平台签名/sha可下载产物存在，且所有产品源码本次未变化。

先单独派发默认outer1460 Normal原生Action，以现有夹具核实双方原Go SYN/SYNACK TCP MSS实际字节、对端解码、Rust预算、双方OS TUN/Wintun读回、真实UDP/TCP、认证、F/R/C及Stop。Normal结果非SUCCESS则**不派发**其余模式；SUCCESS后仅对同源码预编译程序派发显式1500 Normal以及默认1460 Fixed/Auto/Game2/Game4/Game2FEC/Game4FEC七条单模式原生Actions。每一个仍可能FAIL，禁止把派发称为PASS。未重跑完整高吞吐量矩阵。非对称真实人工收窄、原生DF0/DF1、PLAN028–030独立保留。

```feature-impact
{"kind":"none","ids":[],"reason":"H969 only adds strict one-shot native qualification dispatcher and evidence, no product code/feature promotion until signed Actions."}
```
