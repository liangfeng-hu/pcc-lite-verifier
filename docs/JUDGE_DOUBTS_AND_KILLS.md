# Judge doubts & instant kills (demo playbook)

Doubt 1: “This is just JSON theater.”
Kill: Tamper test
- mutate target_digest -> FAIL (missing_or_invalid_targetref)
- add an edge to create a cycle -> FAIL (invalid_tcc_topology)
- change witness_hash -> FAIL (witness_mismatch)

Doubt 2: “You hide the constitution; ‘compassion’ is just talk.”
Kill: Hash commitment
- publicize current constitution_hash_current
- rotate it -> old passes become FAIL (outdated_or_missing_constitution_anchor)

Doubt 3: “You don’t read content; is this just refusal?”
Kill: Boundary + gating
- promise only world-effect no-leak (channel-level)
- fail-closed => no externality, only tombstone
