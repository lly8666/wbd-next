# PLAN029 H1937｜H1936 真TCP失败：测试防火墙远端固定旧 /32

[H1936 原始Win2025/WSL2 Action 43731638265](https://github.com/lly8666/wbd-next/actions/runs/43731638265) 虽全套低价门槛/原Go Rust/Linux构建 PASS，原生第一个A1 `all` 在真实 TCP FAIL：Windows 10.66.0.2→Linux TUN `203.0.113.77` 回声超时，反方向Linux→Windows同样不全；真实内核UDP 25/26 已收，原产品Owned WAL恢复 PASS。原签名产物`plan029-p1-ab/result.json`只有一个 FAIL A1，**后续B1/B2/A2/CPU全部 NOT_RUN**。

原因定位到工作流 TCP功能 listener Defender ACL：`10.66.0.2:45902` 仅在`WBD_PLAN029_V3_DIRECT_SCENE=1`时允许来自 `203.0.113.77`，其余允许旧 `10.66.0.1`；新真正相同Rust V3 all/CN/CN/all四臂都使用Linux TUN owned alias `203.0.113.77`，H1936 A1 没有适用的Windows TCP入站许可。H1937 **只**在`WBD_PLAN029_P1_AB_SCENE=1`且`WBD_PLAN029_P1_POLICY_ABBA_SCENE=1`时选择新public alias，保持原旧P1/普通模式/局域网/原P2源限制，固定本地10.66.0.2/TCP45902，一条源IP，原有readback及owned cleanup不变。

真实新源锁四臂仍未PASS，H1937触发一次。**独立 Direct TCP 小首回包问题**：H1931 首echo-after-half-close p99最高14.957ms、ready wait max16ms，仍 OPEN；本次没有修 Direct 调度，不误报延迟解决；下一步短场384条小TCP真实内核A-B-B-A复测并分层定位 WinSock wake→ready票据→RX回注，不运行10GiB。
