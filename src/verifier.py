import json
import hashlib
from typing import Dict, Any, Tuple, List, Set

# Frozen reason codes (must match spec/REASON_CODES.md)
REASON = {
    "SCHEMA": "schema_invalid",
    "TOPO": "invalid_tcc_topology",
    "TARGET": "missing_or_invalid_targetref",
    "ANCHOR_C": "outdated_or_missing_constitution_anchor",
    "ANCHOR_E": "outdated_or_missing_energy_anchor",
    "COVER": "missing_gatevector_coverage",
    "BUDGET": "egl_budget_exceeded",
    "WITNESS": "witness_mismatch",
}

# Demo minimal required gates (passed output == 0 means "passed")
REQ_GATES_MIN = {
    "G_TOPO",
    "G_TARGETREF",
    "G_ANCHOR_CONST",
    "G_ANCHOR_ENERGY",
    "G_BUDGET",
}

ALLOWED_ACTIONS = {"FAST", "MID", "HEAVY", "EXTERNAL"}


def _sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _canonical_json_bytes(obj: Any) -> bytes:
    # Deterministic JSON encoding
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def compute_witness_hash(env_without_witness: Dict[str, Any]) -> str:
    return _sha256_hex(_canonical_json_bytes(env_without_witness))


def _basic_schema_ok(env: Dict[str, Any]) -> bool:
    try:
        _ = env["proposal_digest"]
        _ = env["action_class"]
        _ = env["energy_est_uj"]
        _ = env["tcc"]
        _ = env["witness_hash"]
        tcc = env["tcc"]
        _ = tcc["root"]
        _ = tcc["receipt"]
        _ = tcc["nodes"]
        _ = tcc["edges"]
        return True
    except Exception:
        return False


def _build_graph(tcc: Dict[str, Any]) -> Tuple[Dict[str, List[str]], Set[str]]:
    adj: Dict[str, List[str]] = {}
    nodeset: Set[str] = set()

    # Add declared nodes
    for n in tcc.get("nodes", []):
        nid = n.get("id")
        if isinstance(nid, str) and nid:
            nodeset.add(nid)
            adj.setdefault(nid, [])

    # Add edges and ensure nodes exist in set
    for e in tcc.get("edges", []):
        a = e.get("from")
        b = e.get("to")
        if isinstance(a, str) and isinstance(b, str) and a and b:
            adj.setdefault(a, []).append(b)
            nodeset.add(a)
            nodeset.add(b)

    # Ensure all nodes in nodeset have adjacency list
    for n in nodeset:
        adj.setdefault(n, [])

    return adj, nodeset


def _is_dag(adj: Dict[str, List[str]], nodes: Set[str]) -> bool:
    # Kahn topological sort
    indeg = {n: 0 for n in nodes}
    for a, outs in adj.items():
        for b in outs:
            if b in indeg:
                indeg[b] += 1
            else:
                indeg[b] = 1

    queue = [n for n, d in indeg.items() if d == 0]
    seen = 0

    while queue:
        x = queue.pop()
        seen += 1
        for y in adj.get(x, []):
            indeg[y] -= 1
            if indeg[y] == 0:
                queue.append(y)

    return seen == len(indeg)


def _reachable(adj: Dict[str, List[str]], root: str, sink: str) -> bool:
    stack = [root]
    seen: Set[str] = set()

    while stack:
        x = stack.pop()
        if x in seen:
            continue
        seen.add(x)
        if x == sink:
            return True
        for y in adj.get(x, []):
            stack.append(y)

    return False


def _find_nodes_by_type(tcc: Dict[str, Any], node_type: str) -> List[Dict[str, Any]]:
    return [n for n in tcc.get("nodes", []) if n.get("type") == node_type]


def verify(env: Dict[str, Any], anchors: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
    # Returns: (ok, reason_code or "OK", debug_info)
    if not _basic_schema_ok(env):
        return False, REASON["SCHEMA"], {"stage": "schema"}

    proposal_digest = env.get("proposal_digest")
    action_class = env.get("action_class")
    energy_est_uj = env.get("energy_est_uj")
    tcc = env.get("tcc")
    witness_hash = env.get("witness_hash")

    if not isinstance(proposal_digest, str) or not proposal_digest:
        return False, REASON["SCHEMA"], {"stage": "schema", "detail": "invalid proposal_digest"}

    if action_class not in ALLOWED_ACTIONS:
        return False, REASON["SCHEMA"], {"stage": "schema", "detail": "invalid action_class"}

    if not isinstance(energy_est_uj, int) or energy_est_uj < 0:
        return False, REASON["SCHEMA"], {"stage": "schema", "detail": "invalid energy_est_uj"}

    if not isinstance(tcc, dict):
        return False, REASON["SCHEMA"], {"stage": "schema", "detail": "tcc not dict"}

    # 1) Topology Gate
    adj, nodeset = _build_graph(tcc)
    root = tcc.get("root")
    receipt = tcc.get("receipt")

    if not isinstance(root, str) or not isinstance(receipt, str) or not root or not receipt:
        return False, REASON["TOPO"], {"stage": "topology", "detail": "missing root/receipt"}

    if not _is_dag(adj, nodeset):
        return False, REASON["TOPO"], {"stage": "topology", "detail": "not a DAG"}

    if not _reachable(adj, root, receipt):
        return False, REASON["TOPO"], {"stage": "topology", "detail": "receipt not reachable from root"}

    # 2) TargetRef Gate
    tnodes = _find_nodes_by_type(tcc, "TargetRef")
    if len(tnodes) != 1:
        return False, REASON["TARGET"], {"stage": "targetref", "detail": f"TargetRef count={len(tnodes)}"}

    td = tnodes[0].get("payload", {}).get("target_digest")
    if td != proposal_digest:
        return False, REASON["TARGET"], {"stage": "targetref", "detail": "target_digest != proposal_digest"}

    # 3) Two Anchors Gate
    anodes = _find_nodes_by_type(tcc, "IntentAnchor")
    if len(anodes) != 1:
        return False, REASON["SCHEMA"], {"stage": "anchor", "detail": f"IntentAnchor count={len(anodes)}"}

    payloadA = anodes[0].get("payload", {})
    hc = payloadA.get("h_constitution")
    he = payloadA.get("h_energy_policy")

    if hc != anchors.get("constitution_hash_current"):
        return False, REASON["ANCHOR_C"], {"stage": "anchor_const", "detail": "h_constitution mismatch"}

    if he != anchors.get("energy_policy_hash_current"):
        return False, REASON["ANCHOR_E"], {"stage": "anchor_energy", "detail": "h_energy_policy mismatch"}

    # 4) Minimal GateVector Coverage
    gnodes = _find_nodes_by_type(tcc, "GateVector")
    if len(gnodes) != 1:
        return False, REASON["SCHEMA"], {"stage": "gatevector", "detail": f"GateVector count={len(gnodes)}"}

    gate_outputs = gnodes[0].get("payload", {}).get("gate_outputs", [])
    if not isinstance(gate_outputs, list):
        return False, REASON["SCHEMA"], {"stage": "gatevector", "detail": "gate_outputs not list"}

    passed: Set[str] = set()
    for it in gate_outputs:
        if not isinstance(it, dict):
            continue
        gid = it.get("gate_id")
        out = it.get("output")
        if isinstance(gid, str) and out == 0:
            passed.add(gid)

    if not REQ_GATES_MIN.issubset(passed):
        missing = sorted(list(REQ_GATES_MIN - passed))
        return False, REASON["COVER"], {"stage": "coverage", "detail": f"missing={missing}"}

    # 5) Budget Gate (demo)
    budget_map = anchors.get("energy_budget_uj", {})
    budget = budget_map.get(action_class)
    if not isinstance(budget, int):
        return False, REASON["SCHEMA"], {"stage": "budget", "detail": "missing budget"}
    if energy_est_uj > budget:
        return False, REASON["BUDGET"], {"stage": "budget", "detail": f"est={energy_est_uj} > budget={budget}"}

    # 6) Witness Gate
    env_wo = dict(env)
    env_wo.pop("witness_hash", None)
    expected = compute_witness_hash(env_wo)
    if witness_hash != expected:
        return False, REASON["WITNESS"], {"stage": "witness", "detail": "witness_hash mismatch"}

    return True, "OK", {"stage": "ok"}
