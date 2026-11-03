# PLAN028 H1041 — Game2 同设备 A→A2+B 原生交接

H1040 已通过 Game2/Game4 同端口双独立组的真实原 Go TLS/原生 Rust M4、真实内层 UDP 和独立 Stop。但那并不覆盖更难的**同一安装身份旧代 A 与新代 A2 重叠、Bob 设备 B 始终不退出**。

在原 Game2 两组 netns 夹具中 opt-in 第四个真实 netns R、真实第二组同 Alice 用户 + 同安装 identity、不同物理 IP/原 TCP 四元组。A 仍活、B 仍活时 R 完成全 2 lane protected TLS；要求 R 从原保护租约获得与 A 完全相等的 /32，服务器只在新的原生 GameAdapter M4/单-reader /32 route Ready 后精确 Stop 旧组 A。B 与 A2 同时真实 UDP；随后只停止旧 A 客户端，B 和 A2 必须继续 UDP，再检查当前两组 native M4 和唯一 shared reader 整体 Stop。

源内容仅新增 opt-in 真实内核断言/namespace，保留原 Game4 双组基础场景不扩模式，未修改原 Go TLS、Rust AEAD/PN、Game 逻辑、FEC 与 wire。成功前只算测试候选；这与 90 秒 Health 死亡时序不等价。

```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient"],"reason":"H1041 exact original Go/Rust real Game2 same protected installation new-generation A2 handover while B independent cohort remains on 443 and one TUN; verify same leased /32 and old exact Stop."}
```
