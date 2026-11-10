# PLAN028 H1508: Windows 五端 H1506 第二次仍止于 Cheap 阶段，保留旧 ABBA 所有权

首次原H778要求具体 legacy 全上传名；二次 Action42765313830 在 `tests.test_delivery_ci.test_same_windows_runner_rust_native_abba_is_exact_source_only` 需要**旧原生全套产物仍在任意成功失败时上传** (`if: always()`)。首次把全上传限制成`if ... matrix.legacy`破坏了这一合同；尚无任何 Npcap Windows5 600s 真正启动。最小修复：单个原上传 step、`if: always()`原样、`name: m0-wl-full-public-normal-direct` 的 legacy 字面原名；若是H1506才在 name 字段附加动态不同的 loss0/loss30 GitHub run ID后缀，避免 v4 artifact 同名。去掉额外的 duplicate uploader。无需削弱原回归断言，更不修改Go/Rust产品。下一次单推送重跑 Cheap 后自动两个独立 Windows VM 600s；当前仍NOT_RUN。

```feature-impact
{"kind":"none","ids":[],"reason":"Restore historical always-run raw native artifact invariants while keeping independent H1506 matrix artifact names."}
```
