# Windows crash / upgrade recovery fix

User reports GUI cannot exit after original child failure, and existing no-WFP v2 WAL refuses recovery demanding live original owner. Separate fix branch from main while PLAN030 test completes. Stop releases dead child independently; GUI attempts native recovery before next connection and can exit with explicit unresolved status. Reuse existing v2 route receipts and native per-interface restore; no WFP guard required for v2. No physical host mutation in this turn; qualification pending. Old script/v1 formats remain separate.
