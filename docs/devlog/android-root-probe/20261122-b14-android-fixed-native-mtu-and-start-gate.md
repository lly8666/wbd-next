# B14｜Android Fixed 原 M4 使用正确 FEC MTU，真实 Native start Gate

基线 B13 SOURCE `273ce9150debdd9a09c2f995fb941c5940574d01` 的原Rust`next_original_record_pn` Android编译条件已修正并正在独立同源CI。B14与其分开冻结SOURCE，不追认旧验收。

## 本片所改的真实原组件

- 已存在的 Rust `FrameBudget::derive` 同一函数供 Android Normal/off 与 Fixed，前者 `FecReservation::FixedOff`，后者 `V3Fec2Fixed`，每方向将原协商 record wire cap、对端真实 MSS、物理 Network MTU 共同约束。Fixed在M3 Repair最大实际大小外多留14B，**不靠纯source 10B头虚增可用TUN MTU**。Go唯一`V4DeriveColdMTUBudget`已经用相同模式；本片不改用户默认1460/显式1500，或造第二Go算法。
- 原 Bionic M4 TX cold frame 按原已认证feature7/feature3选择一次；Native loop_start 仍只接受原 Go完全认证并Det​​ach的generation、原PhysicalNetwork、同一原TUN和RAW，并且feature7额外须有完整的Fixed PENDING、RX原owner、PLAN027 QualityTx、零尚未分类早期M3记录。没有额外TUN reader、系统路由替换或额外crypto/PN。
- 原 Linux/Windows/Android Normal/off保持旧分支；Rust host纯MTU金向量覆盖576/1280/1460/1500与14B差，Android源头代码门和原SDK signed APK门同步。超 MTU IPv4仍不会误用 Normal LINK（Fixed DF0真正IP分片/DF1 PMTU另片）。
- 原 Go`ConnectAuthenticatedPeer`的 Android pre-TLS Fixed/Auto拒绝保留，Root APK默认 Normal/off 不变，Native start 能编译、ABI存在并不证明 Android 手机已运行 Fixed。

## B13 上一轮源码门失败与修正

B13修订 SOURCE `273ce9150debdd9a09c2f995fb941c5940574d01` 的 [dual64 #44926820734](https://github.com/lly8666/wbd-next/actions/runs/44926820734)：Rust/Go双ABI原生构建通过，但 Root App `test-network-scope-gate.sh` Python行124旧静态断言检查`control.low_rate_quality.is_some()`，而B13已改为`if let Some(report)=control.low_rate_quality`且传入真正M2 matcher，故Root APK在此源码门失败；B14将旧断言修正为验证新真实处理语句。不把该FAIL改写成通过。

## 真资格

新SOURCE的 Host/双ABI/签名APK/Linux oracle单独看Action。Android实机、Linux服务端SYN/TLS/lease、Fixed业务和丢包恢复、内层超限大包拆分重组均 NOT_PROVEN。不得将编译PASS写作E2E通过。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B14原Fixed M4与Go冷预算都用Rust同一FrameBudget+14B FEC预留，原TLS feature7/PENDING/QualityRX/OFF early准入唯一Bionic worker；Go产品仍拒绝Fixed，超MTU及真实设备待验。"}
```
