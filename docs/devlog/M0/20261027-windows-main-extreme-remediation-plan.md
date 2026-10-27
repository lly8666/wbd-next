# main Windows 接线审计与完整整改包

用户直接授权：查当前main接线/近期测试/极限参数/Go稳态成本，交付可施工方案和M0提示词，先写完本批代码再集中测试。

审阅源码 c7fef14b6e2443ba432d52478f33c374af6466e7。只读近期Actions与相关源码，没有产品修改、测试dispatch、部署或改写在运行M0的cursor/registry。计划与源码审计分开，历史成功不能延伸成当前产品性能资格。

- 方案：`docs/decisions/M0-WINDOWS-EXTREME-REMEDIATION-20261027.md`
- 核验收据：`docs/evidence/windows-main-audit-20261027.json`
- 执行提示词：`docs/prompts/M0_WINDOWS_REMEDIATION_EXECUTION.md`
- 9d2362d Auto失败artifact SHA256已独立核对，正文只保留非机密统计；未提交原始日志/pcap/凭据。
- 追到6d35857 run40483279255最终FAIL并独立核artifact12724129609/hash：Normal seal拒绝、NPF drop7333；四个Game模式发送阶段FAIL；补入尺寸口径和多模式报告未上传/日志被覆盖的夹具整改，不凭错误字符串认定根因。
- 明确1536首发门控、FEC take错误回收、SEQ半回绕、每包身份/FFI开销、Game容量/单lane隔离、Auto窗口及无界持锁清理、绝对repair帽。Auto428B断裂真实根因待M0复现，未冒充定位完成。
- 顺手修热入口里“开发分支未合main”的过时描述，历史原证据不改。M0实际任务和进度由其接手后自行更新，不代写完成状态。

验证：仅文档/源码/证据审查与计算；本提交的文档治理检查由Actions执行。产品整改、性能和物理资格均NOT_RUN。

```feature-impact
{"kind":"none","ids":[],"reason":"用户授权的施工计划、只读审计和过时入口修正；未修改产品实现、参数默认值或平台资格。M0实施时须更新受影响功能卡。"}
```
