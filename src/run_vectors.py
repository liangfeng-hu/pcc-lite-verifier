import os
import json
import time
import hashlib
from typing import Dict, Any

from verifier import verify, compute_witness_hash


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VEC_DIR = os.path.join(ROOT, "vectors")
OUT_DIR = os.path.join(ROOT, "out")
ANCHOR_PATH = os.path.join(ROOT, "config", "current_anchors.json")


def _sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _ensure_out():
    os.makedirs(OUT_DIR, exist_ok=True)


def _load_anchors() -> Dict[str, Any]:
    with open(ANCHOR_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _append_jsonl(path: str, obj: Dict[str, Any]):
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def _read_bytes(p: str) -> bytes:
    if not os.path.exists(p):
        return b""
    with open(p, "rb") as f:
        return f.read()


def _auto_fill_witness(env: Dict[str, Any]) -> Dict[str, Any]:
    if env.get("witness_hash") == "AUTO":
        env_wo = dict(env)
        env_wo.pop("witness_hash", None)
        env["witness_hash"] = compute_witness_hash(env_wo)
    return env


def main():
    _ensure_out()
    anchors = _load_anchors()

    receipts_path = os.path.join(OUT_DIR, "receipts.jsonl")
    tomb_path = os.path.join(OUT_DIR, "tombstone.jsonl")
    seal_path = os.path.join(OUT_DIR, "ledger_seal.jsonl")
    summary_path = os.path.join(OUT_DIR, "summary.json")

    # Clean previous outputs
    for p in [receipts_path, tomb_path, seal_path, summary_path]:
        if os.path.exists(p):
            os.remove(p)

    files = sorted([f for f in os.listdir(VEC_DIR) if f.endswith(".json")])

    summary = {"ok": 0, "fail": 0, "details": []}

    for fn in files:
        path = os.path.join(VEC_DIR, fn)
        with open(path, "r", encoding="utf-8") as f:
            env = json.load(f)

        env = _auto_fill_witness(env)
        ok, reason, debug = verify(env, anchors)

        ts = int(time.time())
        row = {"file": fn, "ok": ok, "reason": reason, "debug": debug}
        summary["details"].append(row)

        if ok:
            receipt = {
                "kind": "RECEIPT",
                "ts": ts,
                "file": fn,
                "proposal_digest": env["proposal_digest"],
                "action_class": env["action_class"],
                "energy_est_uj": env["energy_est_uj"],
                "epoch": env.get("tcc", {}).get("epoch"),
                "nonce": env.get("tcc", {}).get("nonce"),
                "allow": True,
                "reason_code": "OK",
            }
            _append_jsonl(receipts_path, receipt)
            summary["ok"] += 1
        else:
            tomb = {
                "kind": "TOMBSTONE",
                "ts": ts,
                "file": fn,
                "proposal_digest": env.get("proposal_digest"),
                "action_class": env.get("action_class"),
                "energy_est_uj": env.get("energy_est_uj"),
                "epoch": env.get("tcc", {}).get("epoch"),
                "nonce": env.get("tcc", {}).get("nonce"),
                "allow": False,
                "reason_code": reason,
                "failure_stage": debug.get("stage"),
                "detail": debug.get("detail"),
            }
            _append_jsonl(tomb_path, tomb)
            summary["fail"] += 1

    receipts_bytes = _read_bytes(receipts_path)
    tomb_bytes = _read_bytes(tomb_path)

    seal = {
        "kind": "LEDGER_SEAL",
        "ts": int(time.time()),
        "receipts_sha256": _sha256_hex(receipts_bytes),
        "tombstone_sha256": _sha256_hex(tomb_bytes),
        "root_sha256": _sha256_hex(receipts_bytes + b"\n" + tomb_bytes),
    }
    _append_jsonl(seal_path, seal)

    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print("DONE.")
    print(f"OK={summary['ok']} FAIL={summary['fail']}")
    print(f"Outputs: {OUT_DIR}")


if __name__ == "__main__":
    main()
