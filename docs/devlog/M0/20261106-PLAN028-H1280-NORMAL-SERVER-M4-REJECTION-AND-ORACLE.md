# PLAN028 H1280 — H1279 三场原生验收与 Normal M4 假成功硬门槛

2026-11-06。H1279 [Action42197650482](https://github.com/lly8666/wbd-next/actions/runs/42197650482)，实际SOURCE `5a705e52abd4aa345b5a4738f5c66eb8441cc2d3`，原始Go FakeTCP TLS + Rust原M4、三台原生ARM64各1800秒、五认证客户端。build SUCCESS，baseline SUCCESS，heterogeneous/pressure FAIL。三个ZIP的实际hash已核对并登记：[H1280源证据](../evidence/M0/PLAN028-H1280-H1279-SOURCE5A7-3X1800S-VERIFIED-20261106.json)。

## 证据优先：切勿混淆业务空洞与TC丢包

H1279 Game4 M1消费最多4→8已产生有方向的业务数据面改善，高压Dave服务器独立租约pending overflow从H1278 **6364→352**（下降94.5%），客户端从**3321→121**（下降96.4%），而高压单lane成功仅**9**次、目标至少10次，未达标，且其它客户端共享队列/总业务告警未消除。Baseline五客户端全项通过；异构6项业务/换代告警、Erin Fixed6最长S2C 9460ms；高压8项告警、Erin Fixed6 C2S 6390ms，全部须维持FAIL。原始accepted repeat记录带宽场景baseline/hetero/pressure=0.81921/1.52325/3.11850 Mbps，对应R/(F+R)=0.6959/0.86865/0.94485%，**不含控制C、FEC parity、IP/TCP/L2**。

更严重且能精确交叉定位的另一个根因链：高压 Alice Normal Off、原始TC物理0%注入，10:01:57客户端本地原TLS+Rust M4报告generation=11 READY，立刻真实Stop原generation=10。同一秒服务器日志 `V4_PUBLIC_MIXED_ADMISSION_REJECT stage=normal_rust_owner`，服务端没有该代完整M4。直至10:03:11客户端下一次换代止，gen11原生`V4_PUBLIC_RX_CHAIN raw_observed=0 raw_tuple=0 data_unique=0 tun_delivered=0`；但该代`V4_PUBLIC_TX_CHAIN staged_udp=203375 staged_tcp=29`，真实应用 **73,300ms双向无收包**。因此这不是51个服务端TUN overflow包或Game4容量的充分解释；是**客户端本地READY/Stop与服务端最终Native M4接管缺少对端确认**。旧Normal旋转oracle仅比客户端Ready/Stop数、未独立核服务端，误判PASS_SCOPED。本轮修复后必须fail-closed，不能因旧oracle绿灯就恢复资格。

## H1280 定点产品与Oracle更改（非宣称根因修复）

- 原始Go `bridge_v4_linux_server_product.go` 对已认证Normal原M4的独立阶段设置可`Unwrap`的封闭类型，识别受保护snapshot、lease/share bind、RAW attach、TUN attach、FEC、outer、health、auto、feedback、Rust loop start；保持原错误归属与Stop，**不记录任何认证密钥或原始包**。原 C FFI返回值通过具名status类型保留离散Rust数字错误码，原errors.Is仍成立。
- `game_linux.go` 每个真实server Normal M4 READY或REJECT输出精确原始FakeTCP客户端IPv4 + TCP源端口；REJECT还输出static stage与整数native_rc（缺证据=-1），没有新增wire协议、重试器或认证放宽。
- `path_supervisor_linux.go` 客户端真正promote日志关联同一src IP/port；报告对所有Normal Off/Auto/Fixed6逐个客户端真实generation做**服务端独立原M4成功匹配**，client-local READY绝非证明。真正拒绝、缺日志或对照不全均明确 FAIL_SERVER_NORMAL_M4_COMMIT_MISSING。Game2/4原已有服务端TLS cohort/slot匹配逻辑不变。
- 原始Go unit `TestPLAN028NormalM4StageErrorPreservesEvidenceAndSecrets` 验证typed stage/RC/errors.Is与密钥隔离；Python unit 验证两个不同IPv4相同port不能互相借成功证据及被拒绝的一个generation不可当PASS。旧真实业务性能门槛一项也不放宽。

新 `.github/workflows/m0-plan028-h1280-arm64-30min-normal-m4-stage.yml` 共用同个SOURCE原ARM64 build，三并行1800秒五认证客户端、全方向真实UDP/TCP/gap、p99、CPU/RSS、qdisc、Server/Client独立队列、外层record F/R，报告严格同时要求真实client-server换代、全客户端配置的业务告警为零，全部产物 `if:always()` 上传。若再现原拒绝，需要下一跑次m4_stage/native_rc定位原系统失败；此文不是其根因完成证明。

仍未修完：H998原 same-socket 在线MTU FAIL、旧H1259/H1268 Fixed6 S2C间歇故障、Game4高损冷TLS不足、Fixed6秒级空洞、控制C及全IP成本未测。性能仍UNVERIFIED。

```feature-impact
{"kind":"updated","ids":["linux-raw-tun"],"reason":"Fix Normal Off/Auto/Fixed6 source-specific false-positive local M4 rotation oracle using real independently verified server M4 result, and tag credential-verified Linux original Go/Rust Normal admission stage+typed native RC without changing wire or business data path."}
```
