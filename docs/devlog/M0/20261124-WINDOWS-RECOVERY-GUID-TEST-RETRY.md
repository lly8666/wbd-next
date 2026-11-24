# Windows v2 recovery test GUID representation

45355056087 compiled successfully but all four child scenes exited at the new stale GUID setup with journal conflict. The fixture used a literal lower-case GUID; the inherited inspector requires GUID.String canonical text. Construct the artificial GUID through Windows GUIDFromString and String. No production change; actual gone adapter recovery was not reached. Re-run the existing four scenes and GUI check only.

```feature-impact
{"kind":"updated","ids":["windows-network-wal"],"reason":"真实恢复测试在新增GUID夹具处提前失败，修正规范字符串，不改变生产逻辑。"}
```
