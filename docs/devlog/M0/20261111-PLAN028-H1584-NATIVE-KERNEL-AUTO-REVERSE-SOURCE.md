# PLAN028 M0 H1584｜补齐真正 Linux 内核→Windows 自动租约冷反向业务（2026-11-11）

**IN_PROGRESS，当前修复还不是业务 PASS。**前序 `main@3f82fad808e5ee5a76624c3d47a2c42701c5b62b` H1582 Action `42995018223` 有源锁Windows2025 signed Npcap/Wintun/原Go TLS+Rust M4；双方已认证 AES-256-GCM（cipher ID3），Windows获得真正服务器分配 `10.66.0.130/32`，但第一轮 Rust `TXCopied44, RXDelivered0, TXAfterRX0, Rejected18, WorkerError0` 20s超时，五客户端应用**未启动**。原始 Action **FAIL**，服务端Rust shared TUN `routed=0,reader_joined=1`；Windows WAL没有残留、WSL桥/netem恢复。原始文件 artifact `13844306585`，本案扩展 evidence `docs/evidence/M0/PLAN028-H1581-WIN-AUTO-AES-MIXED-20261111.json`。

与旧 H1577 `cd5dfa3b` 真实150s同类比较：旧场通过 `WBD_PLAN028_WIN_REAL_COLD_SEED` 在原始Go TLS验证并入Rust后，用 **真正 Linux kernel UDP socket** 发送到手动 Alice `10.66.0.2/32`，触发 Windows产品现有严格首反向 Rust M3/内核证明；新的 auto/AES H1582 未启用 `cold_seed`，server log真实 `routed=0`。这**提示**夹具缺少反向业务，不能断言AES/Rust产品无缺陷；只补 source-locked H1581测试夹具不改产品密码协商、发包、Rust确认和Stop硬门。

另 H1583 SOURCE `e207fa95bf861cc63a8bf3b0007db2dae644c7dc` Action `42996888234` 在物理30%损、200ms单程的 Windows手动/32 ChaCha 场同样：真实 TLS认证与两端Rust M4已完成，`TXCopied42,RXDelivered0,TXAfterRX0,Rejected17`，原代码对 `h1579` 设置 `probe=false`，没有启动任何 server echo kernel app；整场 **FAIL**，真实首反向与OS Applied **未证**。不能重写成以前审计猜测的TLS失败；SOURCE620较早TLS first-fault仍留历史。原 artifact `13845650574` 及 evidence `docs/evidence/M0/PLAN028-H1579-WIN2025-LOSS30-ORIGINAL-COLD-TLS-M4-20261111.json`。

**H1584修复与硬门：**
- `tools/m0_plan028_h1548_one_windows_four_linux_600.py` 的已有 `server_echo_py` 保留唯一真实绑定的 `10.66.0.1:45941` Linux TUN UDP socket；H1581 150s auto场在原 `V4_PUBLIC_MIXED_NORMAL_READY` 后从 **Windows原始TLS/Rust输出**读取 `auto_lease=true, cipher=3, /32`，严格确认落于服务端 `10.66.0.128/25` 并非旧 .2，才送 **70个有界真实Linux内核UDP包**到该地址：不能伪造ACK、M3/Health、Wintun命中或注入Rust测试回调。H1581还必须在 READY 后验证源真实启动标记和所选/32一致，然后按旧门验证 signed OS真实/32、五客户端真实150秒双向TCP/UDP、Windows单独Stop后Bob仍真实业务、其余四Linux及Rust共享server Stop和WAL/WSL恢复。若仍没有 `RXDelivered`，仍计产品/路径缺陷，不调低门槛/关闭AES。
- 同一源码也修了 H1579 原缺失的源端：独立30%冷TLS/手动ChaCha调用该真实内核UDP helper，寿命260秒、有界前置真实认证；受保护Rust FIRST+reverse成功和OS /32读回之后才能输出30% `PASS_SCOPED`，不是业务吞吐PASS。**这一30%场景只在另一单独Action以标记 `[plan028-h1579-win30-cold-auth]` 运行，当前H1584提交只标记 H1581 loss0，不重复派发两个场景。**
- 旧 H1566/H1574 完整场的手动 `.2`、FEC Off、Linux/Windows原产品default MTU1460、Windows15s/90s/idle0保持。历史 test-only报告FAIL和产品数据FAIL都保留。

**本会话源代码/静态检验≠新源码运行资格，不能提前将PLAN028改完成。**先看下一Action真正报告首反向是否有实际内核包、Rust M3解密/OS 读回；再决定是否需修AES产品路径。后续还缺Windows AES128/手动、同账号多终端、七模式变更回归、30%真正冷链、路径恢复和综合L3、代表压力/CPU/RSS指标；Android/物理公网/029/030仍范围外。

```feature-impact
{"kind":"none","ids":[],"reason":"H1584 fixes exact source-locked native test fixture to provide required real after-TLS Linux kernel UDP into original Rust first/reverse for auto-IP and loss30; no product source/default/GUI/feature control changes."}
```

## H1584 原始预检结果及 H1585 唯一精确断言修复

`6e907a32b95c138dcbd22e8f95d24063c4ce1f88` Action `42999532461` overall **FAIL_PRE_NETWORK_ONLY**：H1581  cheap unittest 的历史文本门仍要求 `"1" if (cold_seed or h1581) else "0"`，而修复代码在独立H1579真实冷TLS也启用绑定Linux内核后向UDP，此精确字符串已变成 `"1" if (cold_seed or h1581 or h1579) else "0"`。运行器未进入Windows编译/真实I/O，不能说产品通过/失败。原 `42999532288` 治理 **PASS**，维护 `42999532289` 全551仅这一条旧断言FAIL。H1585仅修复测试所检查的真实三条件，真实Linux内核包/认证/首反向/OS Stop门完全保留；新SOURCE的 H1581单场待实际Action收集。不能删原失败。

## H1585 missed workflow dispatch / H1586 exact trigger repair

`9ba9edf88a88039dfe7bfc71b27abe45c72ccc31` 修复H1581三条件源断言，但**仅提交了测试/文档/cursor**；现有 `.github/workflows/m0-wl-public-normal-full.yml` 的 `push.paths` 列了H1579而漏了 `tests/test_m0_plan028_h1581_windows_auto_aes_mixed_scope.py`，因此本次没有新 M0 Windows 网络 Action，不可冒称运行。H1586在**原有**真实Windows/Linux CI工作流路径过滤器补齐该测试文件，依然只通过现有 `[plan028-h1581-win-auto-aes-mixed-150s]` 标记选择单一 `mixed-loss0` 场景；不另造治理框架、不顺带派发30%场。H1586提交后的实际结果需要严格等待原Action和raw报告，保留所有旧FAIL。
