# M0 PLAN026｜Linux 双端 Rust 原生定时 Health TX / Receipt 合包

2026-10-29：在同一个原Go凭据TLS→Rust M1/M3→真实 Linux raw/TUN`sendmmsg`架构内，为 **实际 arm_public_original_m2_feedback 的客户端与服务端** 创建一份无独立线程的 HealthClock，默认15s。业务 DATA 优先：无业务时等最近的反馈/FEC/Health deadline；如已存在 due Receipt 则与 Health合成一个 WBC4 kind1，否则才发独立 Health。所有报文原本M1 AEAD/PN同一state且不产生控制ACK循环；使用原sendmmsg真实 copied-prefix/uncertain/NotSent结果结算，只有 accepted 刷新15s时钟，失败至少1s退避；数据first-copy与Control单独算源业务空闲，不伪造业务last-active。无第二Go sender、每包FFI或独立线程。

此前两端真实M3接收已认可严格Health+Receipt，Windows NativeOwner Heartbeat TX已写入另一候选提交。本提交**不启用**服务端无认证90s主动关断、客户端FIN/Dormant、业务Wake，仍需同代次真实server/client readback和V2空闲180s/阻断恢复测试；不预授予固定/游戏/Auto/物理/CPU资格。

```feature-impact
{"kind":"updated","ids":["idle-rotation-keepalive","linux-raw-tun"],"reason":"Linux原始TLS双端Rust业务TX worker增加15s到期认证Health+M2合包与真实driver sendmmsg回执，不改变原TLS/codec/线程数；死链/休眠/配置/网络资格未验证。"}
```
