# YFCore PCC-Lite Verifier (Open-Verifier)

YFCore PCC-Lite is a proof-carrying “constitution gate” demo: high-risk action requests must carry a verifiable TCC DAG closure anchored to:
- constitution snapshot hash (h_constitution)
- energy policy snapshot hash (h_energy_policy)

The verifier is deterministic and fail-closed:
- PASS -> write a RECEIPT
- FAIL -> write a TOMBSTONE with a stable reason_code
No external executor is included.

## Quick start (Python 3.10+; standard library only)

Run:
python src/run_vectors.py

Outputs:
- out/receipts.jsonl
- out/tombstone.jsonl
- out/ledger_seal.jsonl
- out/summary.json

## Open-Verifier / Closed-Builder

This repo intentionally publishes:
- verifier kernel (src/)
- acceptance vectors (vectors/)
- reason codes + SSOT spec (spec/)
- demo pitch docs (docs/)

This repo intentionally does NOT publish:
- constitution full text (only snapshot hash is used)
- energy policy details (only snapshot hash + demo budgets)
- proof package Builder (generator)

Author: Liangfeng Hu
Company: YFCore Technology Limited (Hong Kong)
