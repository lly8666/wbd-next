# H2417 Linux TCP splice candidate

Experimental WIP only. Rust native owner and kernel pipes; Go cold setup. Original H2228 fixture reused with actual independent origin, NAT comparator and BBR proxy. Push workflow exact SOURCE. No build/measurement qualification at commit time.

```feature-impact
{"kind":"updated","ids":["linux-tcp-splice-proxy"],"reason":"新增实验性Linux服务端透明TCP出口及按socket选择拥塞算法，默认仍NAT。"}
```
