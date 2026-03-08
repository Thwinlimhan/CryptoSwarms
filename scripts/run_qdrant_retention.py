from __future__ import annotations

import os

from memory.qdrant_retention import QdrantRetentionPolicy, apply_qdrant_retention_policy


def main() -> None:
    qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
    policy = QdrantRetentionPolicy(
        collection=os.getenv("QDRANT_COLLECTION", "swarm_memory"),
        ttl_days=int(os.getenv("QDRANT_RETENTION_DAYS", "30")),
        prune_batch_size=int(os.getenv("QDRANT_RETENTION_BATCH", "1000")),
    )

    result = apply_qdrant_retention_policy(qdrant_url=qdrant_url, policy=policy)
    print(result)


if __name__ == "__main__":
    main()
