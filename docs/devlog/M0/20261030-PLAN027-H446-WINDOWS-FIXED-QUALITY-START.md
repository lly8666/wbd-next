# PLAN027 H446｜Windows Fixed 的对等一次性质量窗口

前次真Windows↔WSL2 [Action40985801765](https://github.com/lly8666/wbd-next/actions/runs/40985801765) Fixed失败于旧 WBC4 成熟Applied；H444 Linux Fixed bootstrap已准备 v2 认证窗但Windows仍对任何 Fixed v2信号 `Err(INVALID)`。本次更改Windows原M1/M3/NPF owner：仅feature7 Fixed（Game/Normal off不行）、且真正源+parity已NPF确证复制后，允许创建最多2个 START/CLOSE 低频sender窗；受保护同一M3 opener接收Fixed START最多2次，只有START/ CLOSE期间的数据PN参与RX采样，之后回归静默。Auto持续1024/2s窗口原样保留，健康15s、外层ACK shadow、原密文重传均独立。单测从“Fixed拒绝所有 v2”改为“Fixed首个认证窗口允许但仍无持续Auto”，不会恢复逐record M2。**此为未验证SOURCE候选，Windows Fixed Applied 需要真实对端和同源回归，不标PASS**。

```feature-impact
{"kind":"none","ids":[],"reason":"Windows bounded Fixed bootstrapping source candidate, not qualified product evidence."}
```
