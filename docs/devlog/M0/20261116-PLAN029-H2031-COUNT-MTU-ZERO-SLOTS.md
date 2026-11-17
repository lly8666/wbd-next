# PLAN029 H2031｜真实MTU无余量也消费新流前20–30条/2–3秒额度

- 用户最新限制是**前20..30条合格业务record，前2..3秒窗口**，不是“前20..30条刚好有空位的record”。旧H2025因提议函数最早`current_wire_room==0`直接return，会让满MTU新流过了几秒后第一条小报文再开始窗口，违反真实时间边界。
- H2031将Off单分支保留零开销；Flows/Tls对每条有效新流TCP/UDP业务record先按time/seq检查并消耗1条（包括没有可追加空间的record），最后才按实际room决定0..min(500,real_MTU_room)B。无字节累计/10%预算，业务不拆包/延迟，Direct不调用，原密文重传不再seal。
- 新测试证实40条无MTU空间不能产生第41次填充，第一条无空间record即启动时间窗，3.1秒后无论有多少room都不能再加。H2028旧真实网络和H2030 Game4实测保留不同SOURCE，H2031需再真实抓包。
```feature-impact
{"kind":"updated","ids":["startup-flow-padding"],"reason":"H2031 strictly count all eligible first 20..30 records, including zero MTU room, and start random 2..3s window on first record; no byte budget or Direct side effect."}
```
