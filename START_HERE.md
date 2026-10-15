# 新聊天接手

固定入口：`lly8666/wbd-next`，控制分支 `main`。不要把旧 wobuzhidao 的当前任务或 Longcycle 的研究任务搬来。

## 最小读取集

1. `AGENTS.md` 与 `PROJECT_CHARTER.md`。
2. 远端 main 的 `.governance/project.json`、`.governance/registry.json`。
3. 当前角色的固定提示词与登记分支上的 `.governance/workstreams/<role>/cursor.json`。
4. cursor 所指的当前日志、请求或决策；只有需要时读 `docs/GOVERNANCE.md`。

控制分支决定权限，工作分支决定进度。角色未激活或没有任务时，不能凭提示词自行启动产品实现。

## 同一 agent 回来与全新 agent 完全同样处理

- 查询精确远端 ref，不把上次看到的 SHA 当现在的 HEAD。
- 验证角色、branch、reservation_revision、assignment_epoch。
- 从 cursor.checkpoint_sha 到远端 HEAD **逐提交**核对 changed paths，不能只看净 diff；修改后撤回仍然是发生过的工作。
- 核对 cursor 的 test request：已有 run 先读结果，不重复 dispatch。
- 输出短结论：当前任务、交接判定、测试范围、下一动作；无需复述整部历史。

判定：

- `CLEAN`：事实已被 cursor 覆盖，允许继续；不表示产品通过。
- `RECOVERY_REQUIRED`：有未确认的远端工作/测试结果；先补事实日志与 H。
- `BLOCKED`：身份、分支、祖先关系、证据或权限冲突；先修该边界，独立任务仍可推进。

只有 GitHub Connector 的聊天也可按同样字段手动核查 commits/compare/run/artifact。不能运行脚本不等于可以跳过核对。Actions 可执行 `python tools/governance.py audit --role M0`；该命令只读远端并报告，不自动改状态或触发测试。

## 初次接手本仓库

方案入口为`docs/architecture/README.md`；可直接施工的接口/状态/反例在`docs/architecture/modules/README.md`。先读00公共契约，再按角色只读当前模块和直接依赖。角色是否激活以远端 registry 为准；不要重复启动已经完成的初始化，也不要自行占用模块。不要一次加载全部施工说明和历史。读取当前 project 和角色 cursor 判断已实现/已测范围；模型、治理、组件 PASS 均不等于产品 PASS。

治理 v2：共享范围审计使用主线 `Central worker scope audit` 的精确 SOURCE 收据，不复制检查器到 worker。详见 `docs/GOVERNANCE.md`；历史 Governance 红灯须区分旧审计边界失败与真正测试失败，不能一概覆盖。

当前分配以 main registry 的 `assigned_task` 为准；工作分支 cursor 可能仍记录上一轮。两者不同时读取 registry 指向的本轮决策，保留旧结果后开始已授权的新任务，勿因旧 cursor 的“等待分配”停住。
