# M0 PLAN026 — 修正 Windows non-FEC 编译门（真实首错）

2026-10-29 Windows source56a3d0e6 自动 Rust owner Action40813413425 在没有 `fec2_product_record` 的合法 Normal/off build 出现5个E0412/E0609/E0425/E0599：Game的FEC-only pending type/finish方法、Fixed mode字段与仅限FEC的认证kind1 sealer。此修订仅使真实非FEC构建将Game固定FEC成员正确按 `cfg` 编译，Fixed V2在缺能力时依然 BAD_STAGE；WBC4 Health/Receipt的原M1 AEAD sealer不依赖FEC codec，适用于Normal/off，且没有新wire/Go包pump。没有通过feature gate授予产品任何Game FEC能力；需要等对应编译结果，仍不能宣称产品/网络PASS。

```feature-impact
{"kind":"none","ids":[],"reason":"只修复已有正常Windows non-FEC构建的Rust编译条件和通用kind1 sealer cfg，不修改用户功能启用条件或版本。"}
```
