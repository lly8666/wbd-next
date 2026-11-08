# PLAN028 H1386：ARM64 五客户端原始 TLS443/Rust M4 实时物理 MTU 1500→1280

**结果：PASS_SCOPED_REAL_ARM64_ORIGINAL_GO_TLS443_RUST_M4_LIVE_PHYSICAL_MTU_SHRINK_NEW_EPOCH_RECOVERY_FIVE_CLIENTS_180S**。

- 真原始 [Action 42465059734](https://github.com/lly8666/wbd-next/actions/runs/42465059734) build/scene 全 SUCCESS、2 构建/执行作业；原始 35 文件 ZIP SHA256 `e8d7b5e9b5f4236f91376144a3628b8e4a0922268523830d718f4d027035658f` CRC 全 PASS、Artifact 13611193724。原二进制同 SOURCE `8fd0eb27fbc23f1491e7934baf0f4dee6a282c32`，固定原 Go donor `a7a82db…` 与 Rust 1.85.1。
- 原真实 Linux ARM64 五个真实 Go/TLS443 + Rust M4 活跃客户端/五租约同一服务端180秒。Alice normal、Bob auto、Carol game2、Dave game4、Erin fixed。Alice 原物理源IP **10.25.0.2 保持不变**，在真实 App 起跑 **70.03162秒** 对真实两侧 veth 做 **OS MTU 1500→1280**，没有 link-down、没有仿真 packet/READY。
- 物理 MTU 改动后的原新 Go TLS + Rust M4 完整接入：Alice 认证代 `[1,2,3,4]`，老代精确 Stop `[1,2,3]`；降低前原实际 SYN MSS1420，降低后 1240，服务器确认新 client ports `64791`、`56327`，而非只相信客户端本地 Ready。
- 真业务 Alice 最后一分钟上行 **6.39986/6.40000Mbps (99.998%)**、下行 **6.39952/6.39986Mbps (99.995%)**。含 MTU 变更的中间分钟，上/下行交付 99.502% / 99.565%，不得冒充全程 0 丢包。原轮换总结五用户 `PASS_ALL_FIVE_SCOPED`、alerts **0**。Dave Game4 原独立 lane Hot 2次。服务器五个真实 per lease Rust TUN 队列均 `offered=direct_delivered`、overflow **0**；全五客户 native Stop 完成，服务端 Stop 按原 scene PASS。
- **严格边界：** 这证明**在线物理 MTU 缩小后，通过原受保护新 TLS 认证代恢复业务**，并**没有**证明旧 H998 同一原 TLS socket 原地无需重建就能继续。旧 H998 原失败不删除；不是 Windows Npcap/Wintun，也非物理 WAN/L3 两次1800秒完整长测。
- 不可变原证据：docs/evidence/M0/PLAN028-H1386-SOURCE8FD0-ARM64-FIVE-CLIENT-LIVE-PHYSICAL-MTU-1500-1280-PASS-20261108.json

```feature-impact
{"kind":"none","ids":[],"reason":"H1386 test-only native ARM64 original 180s five-client physical same-IP MTU source-locked proof, no product changes and no feature card modification. Maintain same-socket H998 FAIL distinctly."}
```
