from typing import Any
import math
import logging

logger = logging.getLogger(__name__)

def compute_dag_memory_stats() -> dict[str, Any]:
    from api.dependencies import decision_memory_dag
    nodes = decision_memory_dag.nodes()
    edges = decision_memory_dag.edges()
    
    topic_counts: dict[str, int] = {}
    hypothesis_nodes = []
    
    for n in nodes:
        if n.node_type == "hypothesis":
            hypothesis_nodes.append(n)
        if n.topic:
            topic_counts[n.topic] = topic_counts.get(n.topic, 0) + 1
            
    topic_entropy = 0.0
    if topic_counts and len(nodes) > 0:
        for c in topic_counts.values():
            p = c / len(nodes)
            topic_entropy -= p * math.log2(p)
            
    hypothesis_with_context = sum(1 for n in hypothesis_nodes if n.metadata.get("background_context"))
    recall_hit_rate = (hypothesis_with_context / len(hypothesis_nodes)) if hypothesis_nodes else 0.0

    checkpoint_count = sum(1 for n in nodes if n.node_type == "decision_checkpoint")
    top_topics = [
        {"topic": topic, "count": count}
        for topic, count in sorted(topic_counts.items(), key=lambda item: item[1], reverse=True)[:5]
    ]

    return {
        "node_count": len(nodes),
        "edge_count": len(edges),
        "topic_count": len(topic_counts),
        "topic_entropy": topic_entropy,
        "hypothesis_nodes": len(hypothesis_nodes),
        "checkpoint_count": checkpoint_count,
        "recall_hit_rate": recall_hit_rate,
        "top_topics": top_topics,
    }

def build_lineage_summary(traces: list[dict[str, Any]], strategy_id: str | None = None) -> dict[str, Any]:
    filtered = traces
    if strategy_id:
        filtered = [t for t in traces if t.get("strategy_id") == strategy_id]
        
    optimizer_runs = set()
    hypothesis_ids = set()
    coverage_count = 0
    
    for trace in filtered:
        metadata = trace.get("metadata", {})
        if metadata:
            opt = metadata.get("optimizer_run_id")
            hyp = metadata.get("hypothesis_id")
            if opt:
                optimizer_runs.add(opt)
            if hyp:
                hypothesis_ids.add(hyp)
            if opt or hyp:
                coverage_count += 1
                
    coverage = (coverage_count / len(filtered)) if filtered else 0.0
    
    return {
        "trace_count": len(filtered),
        "coverage_ratio": round(coverage, 4),
        "unique_optimizer_runs": len(optimizer_runs),
        "unique_hypotheses": len(hypothesis_ids),
    }

async def readiness_checks() -> dict[str, str | bool]:
    redis_ok = False
    try:
        from api.dependencies import dashboard_repo
        redis_ok = await dashboard_repo.ping_redis()
    except Exception:
        logger.debug("ping_redis failed", exc_info=True)

    timescaledb_ok = False
    try:
        from api.dependencies import dashboard_repo
        timescaledb_ok = await dashboard_repo.ping_timescaledb()
    except Exception:
        logger.debug("ping_timescaledb failed", exc_info=True)

    return {
        "ok": redis_ok and timescaledb_ok,
        "status": "ready" if redis_ok and timescaledb_ok else "degraded",
        "checks": {
            "redis": redis_ok,
            "timescale": timescaledb_ok,
        }
    }
