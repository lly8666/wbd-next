# H2283 双套三Runner真实TCP 2MiB socket buffer和P99折中

## H2282真实发现与本次目标
同一组Windows2025 + 独立ARM64 Linux kernel relay + 另一台ARM64 Linux TCP server，固定双向每向200ms，0%真实netem drop，源 `cb09a27013e391b338a782b21ead9b82a8f3d675` [Action44930023496](https://github.com/lly8666/wbd-next/actions/runs/44930023496) 七jobs全SUCCESS，四条真实25s内核TCP+160小TCP，A默认/B 8MiB Windows+ARM缓冲/A′默认：A组8.829/**227.397**/8.909Mbps、P99453/**984**/454ms；B组8.095/**339.676**/8.605Mbps、P99469/**594**/469ms。B两组Windows全核CPU12.272%/39.682%，ARM8.688%/17.576%；默认Win bulk实际getsockopt send/recv皆131072B，B均8388608B；ARM默认listener rcvbuf131072B，B实际readback16777216B。该观察局限于OS原生Winsock→ARM内核TCP基线，没有运行原 GoTLS/Rust/Wintun，CPU relay tailscaled单核热点未证实或排除。**8MiB吞吐大幅跃升，但P99升高**，不能直接推送产品默认。

## H2283仅改测试尺寸、保留实际双组和源
- 与H2282完全一致的两个互不共享的真实三机组、相同CI机器类别/同一个SOURCE、相同25s四条真实bulk TCP + 160小TCP echo、同一ARM中继两向实际netem 200ms每向、0%损伤和kernel qdisc非零业务packet计数，顺序 A默认→B两端请求**2MiB** `SO_SNDBUF/SO_RCVBUF`→A′默认。同步留每腿Windows与ARM真实socket readback，原Linux sysctl上限16MiB与A/B/A′相同、Owned Stop finally恢复原值；真receiver goodput、Windows/ARM各自CPU、P50/P95/P99及1s迟回和ARM真实收到字节。两组独立数据均保留，不只选最好。
- H2283由 `WBD_H2283_B_BYTES=2097152` 加 `WBD_H2282_TCP_WINDOW_AB=1` 和 `WBD_H2281_SUSTAINED_TCP=1` 指定；原H2282缺省8MiB值不变，所有原Wintun/NPF GoTLS/Rust运行和产品默认值不变。尺寸严格只许2/8MiB以避免任意调整的隐藏scan。每个runner原业务相同，只改B相同两个端点buffer大小，group内其余变量恒定。仅独立workflow `qa-h2283-dual-arm-relay-window2m-ab-tcp.yml` 在明确commit marker `[m0-029-h2283-window2m-ab-3runner]` 触发昂贵6VM，其余既有H2279-H2282均静态检查/不重复真实网络。
- 预计在约400ms RTT，2MiB×4内核TCP流的粗略在途窗口上限约168Mbps，但实际Windows/ARM缓冲会受系统倍率与竞争窗口影响，**该估算不是预测承诺**，必须以原生server收到byte+Win P99与CPU实测。B P99退化明显则否决2MiB候选或考虑更小1MiB；若显著增益且延迟合理，定位单独sender/receiver侧，进一步验证原WBD产品路径(端点自己TCP窗口受OS限制，不能直接替代产品M1/M4 queue)。TCP真实窗口改善不等于恶劣1/5%丢包修复，原FEC2 ON/OFF仍须独立认证。
- H2281/H2282旧结果保留准确scope，H2282一度中央governance-maintenance因mode测试在无环境变量下假失败，已在 `62b4e66d0482af9277e0f797694f086d589315cc` 修正单测通过，产品runtime不变。PR#68 Draft/M0 PLAN029 Open。

```feature-impact
{"kind":"none","reason":"H2283 modifies only explicit dual-independent 3-runner native OS Winsock/ARM benchmark B socket buffer size from 8MiB to 2MiB, preserving 25s TCP and 160 sparse, CPU and p99 gates; Go/Rust/driver/default/Stop untouched."}
```
