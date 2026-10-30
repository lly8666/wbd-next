# PLAN027 H449｜原Go+Rust M4 Linux Fixed / Auto 真实两端应用读回（仅该范围）

- 冻结原始 SOURCE：`ce568d201681e354e350e80b28feed954d4cbd9d`（包含 H444 Linux Fixed one-shot v2 和 H446 Windows代码；以下仅 **Linux native Go/Rust** 真实执行）。
- 单 Action 独立场景：`M0|V4-WIRING-PARALLEL` [40988303441](https://github.com/lly8666/wbd-next/actions/runs/40988303441)，其内部 per-mode 各单独 GitHub job/VM；FEC Fixed job `123844379020`，FEC Auto job `123844378673`，均 `conclusion=success`。此流程产物只判 first app/Stop，不将product_qualified提升。
- 不可变工件：Fixed [12947589018](https://github.com/lly8666/wbd-next/actions/runs/40988303441/artifacts/12947589018)，Auto [12947364975](https://github.com/lly8666/wbd-next/actions/runs/40988303441/artifacts/12947364975)。已独立解包检查 `real-mode.log`、`real-public-app.log`、`manifest.json`。
- Fixed：`M0_PUBLIC_ORIGINAL_GO_V4_FEC2_REAL_GROUP_APP_FIRST_DELIVERY_PASS mode=fec-fixed delivered=64`。Client 与 Server 各 `M0_PLAN027_FEC_NATIVE_CONFIG_READBACK role=... mode=fixed applied=1 profile=1 pending=false`。两端原TLS对应的Rust M4应用首到与真实Stop；不是逐record M2回执。
- Auto：`M0_PUBLIC_ORIGINAL_GO_V4_FEC2_REAL_GROUP_APP_FIRST_DELIVERY_PASS mode=fec-auto delivered=64`。Client/Server `mode=auto applied=1 profile=5 pending=false`；这里只是一次初始配置读回，没有观察 H0→5/15/30%→120s 低损恢复，也没有动态调档、精确F/R/C或网络吞吐 p99。
- 两种模式完全不依赖旧 WBC4 M2 Receipt，为 v2 authenticated START/CLOSE+summary 更新的真实集成场景；代码Applied内部仍要求真实source+parity M4 copy和有匹配的replay-checked总结。此次读取产品日志不包含收到每个summary的单独详情，不能再扩大认证质量结论。
- Game2/Game4 同Action job success只属原workflow脚手架，尚无足够真实 Game2/4双OS产品证据，此条目不升级。
- **还未验收**：Windows↔Linux同源互通/生命周期/15s健康死亡与热切换，A2/A3/A4/A5，C容量10→50→100→200M及250ms 0/5/15/30和5分钟、R/(F+R+C)等真实指标、剩余故障修复。Linux短场景已获得局部完成证据，不得说整套待验收。
