# PLAN028 M0 H1602｜一台Windows签名Wintun＋四Linux接近实际inner MTU的短原生回声

SOURCE尚待本次提交Action确认为准。沿已有H1565一个Windows签名Npcap/Wintun、四Linux独立原生TUN和单原Go TLS443→Rust M4共享server短场：先五端40次真实OS UDP回声，再**只有H1602标记**追加从Wintun `Get-NetIPInterface ... NlMtu`、Linux每个TUN和shared server TUN `ip -j link`读回的MTU预算。各客户端以`min(自己的inner OS MTU、server shared OS MTU)`验证两种真实内层IPv4总长度`MTU-1`、`MTU`各2次 UDP原字节回声，五端共20次实际首次交付；`MTU+1`设置DF1后只记录OS接受/拒绝，**不冒充有效应用收件**。原Rust/Go产品默认（outer1460、FEC Off、Windows keepalive15/dead90/idle0、Linux rotate0）没有任何改变。

该短场仍要求 Alice Windows先Stop→Bob继续4次真实内核UDP、四Linux及共享server精确Stop、WAL/netem/WSL恢复；末端不做600s/L3资格升级。CI只允许本marker选`mixed-loss0`短场、一个Windows Wintun；**不跑同宿主多个Wintun**，保留H1587旧route WAL FAIL。早已通过的H1600 同账号150s 不重跑。本次先完成fixture+workflow+source test装配，再只派发这一场网络实证。真实验收在Action与原始Strict report返回前 **NOT_RUN**，如OS应用或预算读回失败，不归因产品直到定位第一个真实环节。

```feature-impact
{"kind":"none","reason":"Only source-locked test harness and workflow/strict field checks for one actual OS inner-MTU smoke, no product/GUI/default change."}
```
