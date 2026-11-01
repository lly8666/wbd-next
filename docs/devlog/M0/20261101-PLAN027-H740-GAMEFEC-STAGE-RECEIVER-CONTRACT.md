# PLAN027 H740 — independent GameFEC receiver accepted new numeric supervisor stage tokens

M0 GameFEC only, other work paused; H739 exact SOURCE0264 original signed Game2FEC native run41285808472/watcher41285816289 currently IN_FLIGHT, neither business nor Stop qualified. H738 original supervisor now dispatches SUPERVISOR_20S_ALIVE and SUPERVISOR_60S_ALIVE to a separate GameFEC workflow, but receiver input validator ^[A-Z_]{3,30}$ did not allow their numerals. This is a real lost-evidence fixture contract defect, independent of product. H740 changes only independent receiver validator to ^[A-Z0-9_]{3,30}$, retaining length and sanitized stage/detail/source/run constraints, plus pure regression in existing H726 GameFEC fixture. Already dispatching workflow run uses --ref main, so later receipts may use this updated receiver; older failed receipts are not invented as PASS. This patch is not a product data-plane or Go/TLS/wire change. GameFEC real 480s cancellation still applies. Current source/network result NOT_RUN until Action completes.

```feature-impact
{"kind":"none","ids":[],"reason":"Fix numeric independent GameFEC supervisor stage receipt validation, no product or extra test scenario."}
```
