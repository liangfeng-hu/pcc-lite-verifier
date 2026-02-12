# PCC-Lite (90-second pitch)

1) Pain (10s)
AI risk is not only “wrong text” — it is untrusted world effects (API calls, transactions, device control).

2) What we built (20s)
PCC-Lite: actions must carry a proof package (TCC DAG) anchored to constitution hash + energy policy hash.
Verifier is blind, deterministic, fail-closed.

3) Live evidence (40s)
Run vectors:
- clean_path -> RECEIPT
- change 1 char in target -> missing_or_invalid_targetref
- create a cycle -> invalid_tcc_topology
- change anchors -> outdated_*_anchor
- over budget -> egl_budget_exceeded
- witness mismatch -> witness_mismatch

4) Why it matters (20s)
No proof -> no world effect. Failures leave tombstones (reason_code) for audit.
