# PLAN028 H1362/H1363｜ARM64 单向弱网两轮真实交接

- [H1362 原生 ARM64 Action](https://github.com/lly8666/wbd-next/actions/runs/42447434096) preflight PASS，原始五客户端 TLS443/Rust M4 180s 网络与 Stop 全程完成；旧 CI **FAIL 保留**：测试结束的审计函数里，`spec` 先代表场景配置，随后在客户端循环里被覆盖为单客户端字典，返回时访问 `spec["wrapper_source"]` 触发 KeyError。网络/owner 业务和原通用 rapid report 已完整收集；原始35文件 artifact13604660878 SHA256 `012bfd541c2f621c73e8df900eed34536040aaac7be74fc76842b895ca35f823` CRC PASS。
- [H1363 仅原归档离线重新审计](https://github.com/lly8666/wbd-next/actions/runs/42447846208) **SUCCESS**，artifact13604740958 SHA256 `aa1edc7d8af5acff944e521dd7915de1c6e1d7a3584ac7ed7b64c99eff6e1cc7` CRC2 PASS。唯一修复是从原始场景 `plan["h1362_specialization"]["wrapper_source"]` 读取该元信息；未改产品、L1 证据、原字节、网络或验收阈值，不重跑网络。
- SOURCE `24e1fe6c4eab2a1abb7fb8a6d2093abaf57c0f73`，真正原 Go TLS443 + Rust M4、五租约/单TUN，180s 纯单向用户 UDP，反向用户 UDP/TCP/探针为0。Alice/Bob/Carol/Erin 新代均1→2→3及旧代Stop1、2；纯上行的 Alice、Erin 各两次 `native_rx=0 authenticated_health=1 old_route_revoked=1`，服务端 Normal M4 承诺各3次；Dave Game4 仅 lane1/port59881 与 lane2/port51421 两条热换，由原服务端精确确认，剩余3条健康lane不重启。
- 五真实交付率 Alice1、Bob.999940、Carol.996895、Dave.999404、Erin.977095；最大发送活跃无收件间隔0/10/50/100/120ms。Erin真实物理qdisc丢包上行30.033%、下行30.279%。四阶段宿主4核 busy10.21/13.95/16.07/14.33%；五客户端和服务端 final Stop PASS、server queue overflow0、实际app errors0、capacity flags0。原 `h1286-rapid-report` 的五用户轮换结论为 `PASS_ALL_FIVE_SCOPED` 且0警告。
- 此场对比 H1361 同源码静态单向弱网（600s不轮换）补上真实 owner 交接；保留历史 H1317 SOURCEe61b 96.14/91.83s 原失败与 H1319 SOURCE4c12 正向限定资格，不跨源码泛化。后续重点是 Windows 两个真实独立原生 Wintun/Npcap 设备、L0 所有者/MTU细节及 L3 长测。PLAN028 仍 IN_PROGRESS。

```feature-impact
{"kind":"updated","ids":["arm64-targets"],"reason":"Record source24e real native ARM64 five-client strict one-way 30pct125ms two authenticated Normal cold Health owner turnovers plus independent Game4 hot lanes. Original H1362 CI FAIL preserved and H1363 source-locked 35-file OFFLINE raw PASS indexed."}
```
