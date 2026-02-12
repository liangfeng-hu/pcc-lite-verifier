# SSOT | PCC-Lite (Two Anchors + Minimal Coverage) | Hackathon Release v0.1

Repo: https://github.com/liangfeng-hu/pcc-lite-verifier

This SSOT defines a minimal, verifiable, fail-closed protocol for gating high-risk / external actions.

## 0) Frozen scope (minimal complete)
- Two anchors: h_constitution + h_energy_policy must match current snapshot
- TCC topology: must be a DAG, and root must reach receipt
- TargetRef: must bind proposal_digest
- GateVector: minimal required coverage only (not full constitution)
- Energy budget: energy_est_uj must not exceed per-class budget (demo)

Stop condition: do not add new axes; only hardening and acceptance tests.

## 1) Fail-closed rule (binary gate semantics)
Any failure => no externality; write TOMBSTONE with reason_code; ledger must not break.

## 2) Envelope
Env := <proposal_digest, action_class, energy_est_uj, tcc, witness_hash>
action_class ∈ {FAST, MID, HEAVY, EXTERNAL}

## 3) Hard gates
1) Topology Gate
- TCC must be DAG
- root must reach receipt
Fail: invalid_tcc_topology

2) TargetRef Gate
- TargetRef.payload.target_digest == proposal_digest
Fail: missing_or_invalid_targetref

3) Constitution Anchor Gate
- IntentAnchor.payload.h_constitution == constitution_hash_current
Fail: outdated_or_missing_constitution_anchor

4) Energy Anchor Gate
- IntentAnchor.payload.h_energy_policy == energy_policy_hash_current
Fail: outdated_or_missing_energy_anchor

5) Minimal Coverage Gate (demo)
Required passed gate ids:
ReqGates = {G_TOPO, G_TARGETREF, G_ANCHOR_CONST, G_ANCHOR_ENERGY, G_BUDGET}
Fail: missing_gatevector_coverage

6) Budget Gate (demo)
- energy_est_uj <= energy_budget_uj[action_class]
Fail: egl_budget_exceeded

7) Witness Gate
- witness_hash == SHA256(canonical(Env without witness_hash))
Fail: witness_mismatch
