# PLAN027 H689 — fix exact Game failure-tail credential redaction pattern

H688 added fatal-only client/server tail for source6ece Windows Game2/FEC6 first4%+missing Stop (original Action41238055914 artifact upload ENOTFOUND). On review Python raw string unintentionally contained double literal backslashes `\\\\b` / `\\\\S` / `\\\\1` from JS construction, so the regex would not redact credential fields. H689 corrects that ONE test-only line to true regex word boundary/nonspace and captured name/value with `[REDACTED]`; no product, source b6ece, FEC or other test scenario changed. H688 Actions are ALREADY IN FLIGHT at previous harness SHA; never claim their output was properly credential-sanitized, and never copy any potentially sensitive tail into devlog. On collection read only necessary non-secret error codes and fix actual product source after module diagnosis. No new dispatch from this correction. Whole PLAN027 PARTIAL.

```feature-impact
{"kind":"none","ids":[],"reason":"Fix only failure-path redaction regex in new Game diagnostic harness, no product behavior/config or native traffic/test threshold change; H688 Actions continue undisturbed."}
```
