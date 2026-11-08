# PLAN028 H1400｜修 G2 rev4 授权身份测试夹具，不动产品网络

当前用户已将 PLAN028 冻结 authority 置为 `.governance/registry.json` 的 `reservation_revision:4`。原 G2 证明脚本历史硬编码3导致每次 Rust engine 改动的 G2 被拒，本轮 H1398 随口径已修成精确4，实际 [G2 Action42484008957](https://github.com/lly8666/wbd-next/actions/runs/42484008957) 双阶段原生 Rust bootstrap BUILD+CONSUME SUCCESS。

独立 [governance-maintenance Action42484008956](https://github.com/lly8666/wbd-next/actions/runs/42484008956) **原 CI FAIL 保留**：`tests/test_g2_bootstrap_identity.py` 仍把测试仓库假设为 rev3（过去有效），新真实脚本正确拒绝为 `G2 registry revision changed`，以致应分别验证 M4 revoked lease / worker future revision 的断言根本走不到。仅修测试假数据为现行合法 rev4，未来无效改 rev5，并加过期 rev3 反例。真实M4 revoked epoch2 和历史 cursor rev2、角色允许路径和身份校验不变。该问题只影响 G2/governance 的 CI，不给任何网络功能额外 PASS、也不调度网络任务。

```feature-impact
{"kind":"none","ids":[],"reason":"Update stale governance G2 synthetic unit fixture to authorized revision 4; no product wiring or delivery contract change."}
```
