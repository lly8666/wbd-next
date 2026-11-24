# B66｜系统 IPv4 普通 DNS：原 UID / Network 归属、UDP/TCP 同一 owner

B65a `7df9abc6936a495c61771267071808c94b13023c` [Dual64 #45316734334](https://github.com/lly8666/wbd-next/actions/runs/45316734334) 11 SUCCESS/4 SKIPPED，治理通过；实体未验。

Android R+ resolver 对查询 socket fchown 发起应用 UID；Linux RPDB sk_uid 与 iptables owner 的创建者凭据不同。依据 AOSP DnsResolver [resolv_private.h](https://android.googlesource.com/platform/packages/modules/DnsResolver/+/refs/heads/master/resolv_private.h) 与 [resolver test helper](https://android.googlesource.com/platform/packages/modules/DnsResolver/+/ca1ef6511fa4cdedf16409326cc35b23b68e8e09/tests/resolv_test_utils.h)。B66可选普通 IPv4/53：同原单/组/all UID范围，当前 Network 的 netId mark，iif lo，UDP/TCP dport53 的专有19845表和9100..9459优先级；仅这组实际内核选路进入带所有权alias的dummy输出，由两条精确 OUTPUT NAT REDIRECT 交给原B64 loopback同端口UDP/TCP服务。原物理/隧道/CN8503 DNS wire、UDP同端点TCP回退、EDNS cap、原认证lease/TUN-bound upstream；普通数据继续唯一Rust M4。无需猜测netd root UID或修改全局netd配置。原B64选项仍独立，系统选项包含TCP。批量ip规则，专有journal/Stop/Restore；四槽SAF及冷恢复保存。Host真实DNS loopback及内核命令seam，不是Android运行证明。依赖实际resolver socket UID、所选netId与内核RPDB/dummy能力。DoT/DoH、IPv6 DNS目的、未选Network不接管；不修改Private DNS设置。实体NOT_RUN。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B66所选UID和实体Network系统普通IPv4 UDP/TCP53原生RPDB、局部NAT、原DNS服务及原Rust隧道、配置Stop/Restore候选接线。"}
```
