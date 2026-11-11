# PLAN028 H1557 — feature-card 16KiB gate only

Source `693ec6f7f81ae27a451805a1bbab3344bacac79d` Feature catalog failed the existing <=16KiB regular JSON limit after H1556 pretty-print; governance succeeded. This is metadata FAIL, not native product FAIL. Compact `tls-auth-multiclient.json` to **16296 UTF-8 bytes**, preserve existing historic verification rows and the general Win/Linux NOT_RUN, remove two newly-added duplicate H1555/H1556 scope rows. The original fe5a8fa loss0/loss30 FAIL remains permanently in `docs/evidence/M0/PLAN028-H1555-MIXED-NATIVE-LEASE-ROOT-20261111.json`. No Go code/assembly/fixture change, no manual network dispatch.

```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient"],"reason":"Keep bounded existing feature-card JSON syntax and retained verification while repairing presentation only; previously updated protected credential-bound auto lease behavior and scope unchanged."}
```
