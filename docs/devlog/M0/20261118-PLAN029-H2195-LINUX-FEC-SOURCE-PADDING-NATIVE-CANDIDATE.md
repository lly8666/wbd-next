# H2195｜PLAN029 Linux FEC Fixed/Auto 启动填充候选（未验）
 
继H2193 Normal/off双ISA原Go TLS/Rust source 06bd63f5 4/4真网签名后，修复Linux Normal `fec-fixed` / `fec-auto` 先前非off拒绝：在**现有受保护FEC source kind2** 的AEAD marker之后、tag之前按原Rust TunnelStartupPadding算法附加有界随机0尾部。旧FixedStream source_bytes、block/index、revision、parity/repair(kind3)、真实PN/lease/epoch、MTU、原密文一律不改，仍由一原Rust M4完成，Off不建256流跟踪。只实际syscall copied的源PN能进入低频只读计数，helper accepted不是PASS。无Go逐包回调/新wire。

测试只选Fixed/tls与Auto/flows每ISA一原真实Go TLS/Rust客户端+服务端独立场（2/ISA），校验本地非法模式拒绝、正值原raw M4 copied、两端真正内核TCP/UDP、owned IPv6、MTU1460/1389与Stop，旧H2186 16场及H2193 4场不重跑。候选生产SOURCE尚未冻结，真实结果严格NOT_RUN。既有FEC codepath仍应当支持未启用off、正常无损传输；真实高丢恢复、CPU/p99、manual物理MTU/实体ARM不在此轮冒称通过。

```feature-impact
{"kind":"updated","ids":["startup-flow-padding","linux-raw-tun","fec-fixed","fec-auto"],"reason":"H2195 source-only AEAD-tail FEC Fixed/Auto original Linux padding opt-in and 2/ISA native fixture; all updated verification records marked NOT_RUN until SOURCE-locked original kernel evidence."}
```
