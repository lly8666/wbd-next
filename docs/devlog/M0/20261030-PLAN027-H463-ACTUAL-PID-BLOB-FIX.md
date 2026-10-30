# PLAN027 H463｜H462丢失的双美元符PID原样修复

H462 Git diff及run40999231338证实原`echo $$`没有落到Git blob：此前JS `String.replace(old,'$$')`把替换参数中的美元逃逸为一个`$`，单测assertIn/NotIn也同样折叠。H463改用函数替换的两个真实美元字节，保证start-linux.sh将自身有效PID存入owned pid文件，新的单测分别校验双美元存在/单美元不存在。

H461 true Auto M4 error 32621976/40s和Parity计划9发送0仍是阻断，C10真实业务子阶段通过但restart/Stop失败仍保留，不能因为H463 test修复宣布B/C PASS。由新SOURCE一次构建合格后，独立Auto诊断和C10 owned Stop复测，旧二进制不混用。

```feature-impact
{"kind":"none","ids":[],"reason":"Fix previously missing actual shell PID/test source blob with exact $$ bytes; no protocol change."}
```
