# H2148｜廉价门旧完整命令字符串同步

[H2147 Action44225030401](https://github.com/lly8666/wbd-next/actions/runs/44225030401) **FAIL_CHEAP，原生NOT_RUN**。唯一报错是静态`tests.test_m0_plan029b_game_scope`仍精确匹配旧命令`...game_scope -v`，而H2147已将实际CI命令扩展为`...game_scope tests...game2_tcp_scope -v`。更新断言要求两个真实廉价测试都调用，保留真实原始Game2后置TCP和Game4冷配置门。产品Go/Rust/assembly pin未修改；新SOURCE单Game2真实签名必须自己通过，绝不借历史Game4绿灯。

```feature-impact
{"kind":"none","ids":[],"reason":"Only sync legacy static CI selector assertion with expanded existing game scope + real Game2 post-Apply TCP tests; no product change."}
```
