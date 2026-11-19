# H2184｜Game跨平台填充已完成六场/ISA，动态MTU自动重认证在手动IP场景不适用

[H2183真实原生Action44267345357](https://github.com/lly8666/wbd-next/actions/runs/44267345357) SOURCE `c4675f5a85e2e275480719bfa076201c1fcb4915`，x86_64与aarch64两独立真实native Linux 原Go TLS客户端/服务端＋Rust M4均构建成功，每ISA六独立受认证的Game场**实际PASS_SCOPED**：Game2 off、TLS shaped application startup、flows outer-repair off、Game2 fixed6 flows、Game4 fixed6 flows、Game4 off immediate-copy flows；真实内核TCP/UDP两向、双TUN/Stop，Rust原AF_PACKET成功send后pad字节（不是Go填充需求）每端均实测非0且0B off。旧源仍是整体FAIL，因此不虚称六场为整个工作流SUCCESS。

**首个真实失败**：第七场名称`normal-aes128-live-mtu`错误沿用历史手动TUN IPv4 netns夹具，直接同时把物理veth 1500→1280。x86和ARM64两端的原Normal加密/初始双向TCP/UDP/ICMP、AEAD、Stop均已通过，但物理缩窄后64B ICMP客户端→服务端3/3丢失；原日志没有`V4_PUBLIC_PATH_EFFECTIVE_CHANGED`。核当前正式`linux.go`：`runOriginalLinuxClientPaths`与`watchOriginalLinuxUnderlay`仅`role=client && cfg.autoIP`路径启用，手动固定IPv4原CLI走legacy冷持有owner，**不提供无缝物理链路变化自动重认证承诺**。这次真实FAIL保留，不降低收窄小包本应正确交付的任何合格条件，也不把手动模式故障误写为新padding bug。

H2184仅更改新实验矩阵第七场为`normal-aes128`（原Go TLS Rust真实业务和Stop，不触发未支持的手动动态MTU），第八场继续`normal-aes256-x25519-mtu1280`，以已存在`--outer-mtu 1280`静态真实OS MTU和**无预共享route-key的原X25519→TLS认证**补齐CLI功能。Auto-IP路径物理MTU1500→1280→1500需要专用自动租约/共享Rust reader/旧新代重叠的单独两端夹具；本批明确NOT_RUN，不把静态1280称动态恢复。旧H2173 Linux基础10/10源锁证据保留；H2183原8场整体红灯保留，完整029技术仍OPEN。

```feature-impact
{"kind":"none","ids":[],"reason":"Change only supplemental native Linux test scope: correct manual IPv4 fixture's unsupported live physical reauthentication request, retain historical real failure; preserve tested Game padding source and strict original TCP/UDP/Stop/MTU. No product behavior changed."}
```
