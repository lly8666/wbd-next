# M0 PLAN028 H1583｜独立 Windows 30% 真实冷TLS/M4 首因复验（2026-11-11）

**派发前：NOT_RUN；PLAN028 IN_PROGRESS。**H1582 SOURCE `3f82fad808e5ee5a76624c3d47a2c42701c5b62b` 的 Windows 自动/ AES256 + 四Linux 0loss200ms 真150s场景 Action `42995018223` 仍 in_progress，不派发相同场景。当前独立单场通过提交标签 `[plan028-h1579-win30-cold-auth]` 触发，在另一 Actions Windows2025 VM 上对原始签名Npcap+Wintun/原始Go credential TLS443/Rust M4验证**一个** Windows手动/32 ChaCha首次冷认证，物理外层双向各30%损、单程200ms。

## 原问题和当前最小可证伪范围

旧 SOURCE `6207858bac1d2a74bd560f7e2b7f649df887c066` Action `42942358907` 真30%场下观测 SYN/SYNACK MSS1420，但受保护 TLS 冷建链超时于原生 M4 前；旧 H1579 `42984484582` 仅廉价预检失败，真网络并未进入。两者保留，不认为问题已修复。现本轮源已通过Windows Go/Rust + 同源 Linux正式构建（上个0%场），而新测试继续复用现有 `tools/m0_plan028_h1548_one_windows_four_linux_600.py --scene loss30` 及其 `h1579` 分支。

**硬门：**Windows2025真实原生签名Npcap/Wintun和Linux WSL2原始TLS443共享服务端、预共享route-key、真实账户和服务端手动 `10.66.0.2/32`；原始FakeTCP真实SYN→标准TLS证书/认证→Rust M4 `WBD_WINDOWS_CLIENT_READY`，服务端 `V4_PUBLIC_MIXED_NORMAL_READY`，PowerShell真实Get-NetIPAddress必须读到Wintun /32，Windows原生rust/WAL退出、Linux server Rust shared-TUN owner Stop与reader_joined1、Windows netem及WSL bridge/veth恢复。原始报告 `h1548-loss30-strict-native-report.json` 的 SOURCE、真实stage、各资源清理标记与原始log全保存。原 160s ready deadline是单试验有界观察，不是承诺建链SLA。任何一阶段失败，定位 first fault，不改产品硬门或改作PASS。

**NOT_RUN / 不冒充：**30% 下的实际TCP/UDP业务、5客户端同服30%弱网、150s/600s吞吐、250ms单程压力、两场1800s L3、Windows Auto+AES、物理公网/Android/029/030。若首次冷TLS过不了，先定位真实SYN/SYNACK/TLS/健康控制，不循环盲跑更重同族，不因成功包p99替代未交付。该Action的 SOURCE 与 H1582 零损不同，绝不可相互充当业务验证。

派发后的原始Action结果按结论另记；本记录只说明为什么单独跑这一场和应如何判定。

```feature-impact
{"kind":"none","ids":[],"reason":"H1583 only requests one independently source-locked original signed Windows 30% cold TLS first-fault test; no product runtime/default or new feature changed."}
```
