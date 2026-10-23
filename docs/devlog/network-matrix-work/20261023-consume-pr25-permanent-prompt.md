# 将PR25最新永久提示词实际引入网络测试分支

用户要求将此前遗漏的提示词合入。目标是 `experiment/network-matrix-tuning`，读取远端基点 `8a993bf4` 后在隔离worktree消费PR25的 `85e63eba2e05ea48779db3b555fcd34c446d5de6` 文档增量；不操作其他agent的工作目录，不合main。

解决永久提示词及诊断手册的旧文档冲突：引入长期方法、当前计划、实际status三者分离的入口，移除重复首轮ARM适配、历史SOURCE/旧任务起点等命令；补齐此前未消费的独立网络岗位自主诊断/修复权限说明。新增计划入口同时明确最新FEC独立分工，以及单TCP资格不能由多流替代、最终残余不能替代修复及时性。现有TCP buffer/reordering反证继续有效，具体下一步仍由原status记录。

本次只改START_HERE和相关docs。未改产品、夹具、workflow、请求或 `docs/evidence/network-matrix-work/status.json`；产品SOURCE、在途请求、历史FAIL/资格完全保持。未dispatch或执行产品测试。检查文档引用、冲突标记及diff空白；推送使用普通fast-forward，远端若前进先吸收增量，不force push。

这里的合入只指测试分支消费提示词；PR25整体仍未因此合入main。
