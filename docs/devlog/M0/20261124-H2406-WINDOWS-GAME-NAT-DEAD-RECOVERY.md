# H2406 Windows Game NAT dead recovery

A NAT mapping can expire or change with unchanged local Windows interface and IPv4. Windows Game already has a native authenticated HealthClock, but DeadPeer returned generic BAD_STAGE=3 and Go interpreted every worker code as driver failure. Use the existing Normal worker status 6 only at actual Game DeadPeer; acknowledge it as a drained TX worker after real Join and use the common Go cold supervisor after owned Stop. Cold retry is the same bounded original transport retry, fresh source group from H2400. Stop errors do not authorize another generation. No new probe, no idle timer policy change, no new hot worker. Windows native independent one-lane rotation is not introduced here; Linux Game4 has that existing path. Source-specific native/physical recovery pending.

```feature-impact
{"kind":"updated","ids":["windows-native-transport","game-lanes"],"reason":"Existing Game Health90 terminal status feeds common original cold recovery after owned Stop; NAT changes without OS event can recover."}
```
