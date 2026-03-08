from memory.qdrant_retention import QdrantRetentionPolicy, apply_qdrant_retention_policy


def test_apply_qdrant_retention_policy_success():
    captured = {}

    def fake_post(url, payload, timeout):
        captured["url"] = url
        captured["payload"] = payload
        return {"status": "ok", "result": {"operation_id": 1}}

    result = apply_qdrant_retention_policy(
        qdrant_url="http://localhost:6333",
        policy=QdrantRetentionPolicy(collection="swarm_memory", ttl_days=30),
        post_fn=fake_post,
    )

    assert result["ok"] is True
    assert "swarm_memory" in captured["url"]


def test_apply_qdrant_retention_policy_failure():
    def fail_post(url, payload, timeout):
        raise RuntimeError("connection failed")

    result = apply_qdrant_retention_policy(
        qdrant_url="http://localhost:6333",
        policy=QdrantRetentionPolicy(collection="swarm_memory", ttl_days=30),
        post_fn=fail_post,
    )

    assert result["ok"] is False
    assert "connection failed" in result["error"]
