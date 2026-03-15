# CryptoSwarms Memory Subsystem Audit

**Audit Date:** March 15, 2026  
**Scope:** Complete memory architecture analysis including Mem0+Qdrant, Graphiti+Neo4j, and Layer 2 cache

## Executive Summary

The CryptoSwarms memory subsystem implements a three-tier architecture but suffers from **critical implementation gaps** and **state corruption risks**. While the conceptual design is sophisticated, the actual implementation has significant deviations from the documented architecture, missing components, and dangerous failure modes.

**Overall Memory System Score: 4/10** - Conceptually sound but dangerously incomplete

---

## **Component 1: Mem0 + Qdrant (Fast Semantic Memory)**

### Implementation Status: ⚠️ **PARTIALLY IMPLEMENTED**

**Files Analyzed:**
- `memory/agent_memory.py` - Unified memory client
- `memory/qdrant_retention.py` - TTL cleanup policy
- `memory/runtime_memory.py` - Protocol abstractions

### 1. Data Writing After Agent Actions

**Status: ❌ BROKEN**

```python
# From agent_memory.py - AgentMemory.remember()
def remember(self, text: str, important: bool = False) -> None:
    """Store a memory item and optionally promote it to temporal memory."""
    self.fast.add(text, user_id=self.agent_id)  # ✅ Writes to Mem0
    if important:
        asyncio.run(  # ❌ DANGEROUS: Blocking async call in sync method
            self.graph.add_episode(
                name=f"{self.agent_id}_{int(time.time())}",
                episode_body=text,
                source_description=f"Agent: {self.agent_id}",
            )
        )
```

**Critical Issues:**
- **Blocking async calls**: `asyncio.run()` in sync method can deadlock
- **No error handling**: Mem0 failures are silent
- **No transaction safety**: Partial writes between Mem0 and Graphiti
- **Memory leak risk**: Failed writes accumulate in memory

**Usage Pattern Analysis:**
```python
# From runtime_memory.py - AgentMemoryRecorder
def remember(self, text: str, important: bool = False) -> None:
    if self._client is None:
        self._client = self._build_client()  # Lazy initialization
    if self._client is None:
        return  # ❌ Silent failure - no logging
    try:
        self._client.remember(text, important=important)
    except Exception:  # ❌ Catches ALL exceptions silently
        return
```

**Actual Usage in Codebase:**
- ✅ Research connectors use `AgentMemoryRecorder("research_camoufox")`
- ✅ Market scanner uses `AgentMemoryRecorder("market_scanner")`
- ❌ **No usage in backtesting or execution layers**
- ❌ **No usage in decision council**

### 2. TTL Expirations and Stale Data Eviction

**Status: ⚠️ MANUAL ONLY**

```python
# From qdrant_retention.py - Manual cleanup script
def apply_qdrant_retention_policy(
    *, qdrant_url: str, policy: QdrantRetentionPolicy, ...
) -> dict[str, Any]:
    endpoint = qdrant_url.rstrip("/") + f"/collections/{policy.collection}/points/delete"
    payload = {
        "filter": {
            "must": [
                {
                    "key": "created_at_epoch",
                    "range": {"lt": f"now-{policy.ttl_days}d"},  # 30-day default TTL
                }
            ]
        },
        "limit": policy.prune_batch_size,  # 1000 batch size
    }
```

**Critical Issues:**
- ❌ **No automatic TTL**: Requires manual script execution (`scripts/run_qdrant_retention.py`)
- ❌ **No monitoring**: No alerts when cleanup fails
- ❌ **Batch limitations**: 1000-point limit may not clear all expired data
- ❌ **No verification**: No check that expired data was actually deleted

**TTL Configuration:**
- Default: 30 days (`QDRANT_RETENTION_DAYS=30`)
- Collection: `swarm_memory`
- Batch size: 1000 points per cleanup

### 3. Qdrant Embeddings Query Usage

**Status: ✅ IMPLEMENTED BUT BYPASSED**

```python
# From agent_memory.py - Semantic search implementation
def recall(self, query: str, limit: int = 5) -> list[str]:
    """Return relevant fast-memory hits for a semantic query."""
    results: dict[str, Any] = self.fast.search(query, user_id=self.agent_id, limit=limit)
    return [result["memory"] for result in results.get("results", [])]
```

**Analysis:**
- ✅ **Proper Mem0 integration**: Uses Mem0's search API which queries Qdrant
- ✅ **User isolation**: Searches scoped by `user_id=self.agent_id`
- ✅ **Configurable limits**: Default 5 results, configurable

**BUT: Critical Usage Gap**
```bash
# Grep results show NO usage of recall() in main codebase
# Only test files and example scripts use semantic search
# Research factory uses DAG recall instead of Qdrant embeddings
```

**Bypass Pattern:**
```python
# From research_factory.py - BYPASSES Qdrant entirely
def _recall_context_nodes(self, *, topic: str, now: datetime) -> list[MemoryDagNode]:
    walker = DagWalker(self.memory_dag)  # Uses in-memory DAG instead
    result = walker.recall(topic=topic, lookback_hours=72, max_nodes=4, token_budget=500)
    return result.nodes
```

### 4. Memory State on System Kill/Restart

**Status: ❌ CATASTROPHIC DATA LOSS RISK**

**Mem0 Persistence:**
- ✅ **Qdrant persistence**: Data survives restarts (stored in Docker volume)
- ✅ **Collection durability**: `swarm_memory` collection persists

**Runtime Memory Persistence:**
- ❌ **AgentMemoryRecorder state lost**: Lazy-initialized clients reset
- ❌ **No graceful shutdown**: No cleanup on process termination
- ❌ **Connection state lost**: Qdrant connections not pooled

---

## **Component 2: Graphiti + Neo4j (Temporal Knowledge Graph)**

### Implementation Status: ⚠️ **PARTIALLY IMPLEMENTED**

**Files Analyzed:**
- `memory/agent_memory.py` - Graphiti integration
- `infra/docker-compose.yml` - Neo4j container setup

### 1. Data Writing After Agent Actions

**Status: ❌ BROKEN - ASYNC/SYNC MISMATCH**

```python
# From agent_memory.py - Dangerous async pattern
def remember(self, text: str, important: bool = False) -> None:
    self.fast.add(text, user_id=self.agent_id)
    if important:
        asyncio.run(  # ❌ BLOCKING: Can deadlock if called from async context
            self.graph.add_episode(
                name=f"{self.agent_id}_{int(time.time())}",  # ❌ Collision risk
                episode_body=text,
                source_description=f"Agent: {self.agent_id}",
            )
        )
```

**Critical Issues:**
- **Deadlock risk**: `asyncio.run()` in sync method can deadlock existing event loops
- **Name collisions**: Episode names use `int(time.time())` - collision risk in high-frequency scenarios
- **No error handling**: Graphiti failures are silent
- **No transaction coordination**: Mem0 write succeeds but Graphiti fails = inconsistent state

### 2. TTL Expirations and Graph Growth

**Status: ❌ NO TTL IMPLEMENTATION**

```python
# No TTL mechanism found in Graphiti integration
# Episodes accumulate indefinitely in Neo4j
```

**Critical Issues:**
- ❌ **No automatic cleanup**: Neo4j graph grows unbounded
- ❌ **No retention policy**: Old episodes never expire
- ❌ **Memory leak**: Graph size will grow linearly with system usage
- ❌ **Performance degradation**: Large graphs slow down queries

**Neo4j Configuration:**
```yaml
# From docker-compose.yml
neo4j:
  image: neo4j:5
  environment:
    NEO4J_AUTH: neo4j/neo4j_change_me
  volumes:
    - neo4j_data:/data  # Persistent storage
```

### 3. Temporal Graph Growth and Duplicate Detection

**Status: ❌ NO DUPLICATE PREVENTION**

```python
# From agent_memory.py - No deduplication logic
async def add_episode(name, episode_body, source_description):
    # Graphiti core handles this - no visible deduplication
```

**Analysis:**
- ❌ **No duplicate detection**: Same content can create multiple episodes
- ❌ **No content hashing**: No mechanism to detect similar episodes
- ❌ **No relationship merging**: Contradictory facts can coexist
- ❌ **No fact validation**: No mechanism to resolve conflicts

**Potential Issues:**
- **Graph pollution**: Duplicate episodes waste storage and confuse queries
- **Contradictory facts**: No mechanism to handle conflicting information
- **Query performance**: Duplicates slow down search results

### 4. Memory State on System Kill/Restart

**Status: ✅ PERSISTENT BUT UNMANAGED**

**Neo4j Persistence:**
- ✅ **Data survives restarts**: Neo4j data persisted in Docker volume
- ✅ **Transaction durability**: ACID properties maintained
- ❌ **Connection management**: No connection pooling or graceful shutdown
- ❌ **Orphaned connections**: Killed processes leave connections open

---

## **Component 3: Layer 2 SQLite Cache (TTL Tiers)**

### Implementation Status: ❌ **MAJOR ARCHITECTURE DEVIATION**

**Expected:** SQLite + TTL tiers  
**Actual:** Redis + In-memory DAG + JSON persistence

### 1. Data Writing After Agent Actions

**Status: ⚠️ INCONSISTENT IMPLEMENTATION**

**Redis TTL Implementation:**
```python
# From core_adapters.py - RedisKeyValueStore
def setex(self, key: str, ttl_seconds: int, value: str) -> None:
    self.client.setex(key, ttl_seconds, value)  # ✅ Proper TTL support
```

**Usage Patterns:**
```python
# From risk_monitor.py - Heartbeat TTL (600s = 10min)
self._heartbeat_store.setex("risk_monitor:heartbeat", self._heartbeat_ttl_seconds, now.isoformat())

# From storage.py - Heartbeat protocol
def set_heartbeat(store: KeyValueStore, record: HeartbeatRecord) -> None:
    store.set(heartbeat_key(record.component), _utc_iso(record.timestamp))
    # ❌ NO TTL: Uses set() instead of setex()
```

**Critical Issues:**
- ❌ **Inconsistent TTL usage**: Some components use TTL, others don't
- ❌ **Protocol violation**: `KeyValueStore` protocol has no TTL method
- ❌ **Missing SQLite**: No SQLite implementation found despite architecture docs

### 2. TTL Tier Correctness

**Status: ⚠️ PARTIALLY CORRECT**

**Documented TTL Tiers:**
- Heartbeats: 10 minutes (600s)
- Decision checkpoints: 72 hours
- Research context: 72 hours

**Actual Implementation:**
```python
# ✅ CORRECT: Risk monitor heartbeats
heartbeat_ttl_seconds=600  # 10 minutes

# ❌ MISSING: Decision checkpoints have no TTL
# Stored in MemoryDag with JSON persistence - no expiration

# ❌ MISSING: Research context has no TTL  
# Stored in MemoryDag with provenance decay but no deletion
```

**Memory DAG "TTL" via Provenance Decay:**
```python
# From dag_recall.py - Soft expiration via confidence decay
def _provenance_confidence(*, node: MemoryDagNode, now: datetime, half_life_hours: int) -> float:
    age_hours = max(0.0, (now - node.created_at).total_seconds() / 3600.0)
    hl = max(1.0, float(half_life_hours))
    decay = 0.5 ** (age_hours / hl)  # Exponential decay
    return max(0.0, min(1.0, base_conf * decay))
```

**Issues:**
- ⚠️ **Soft expiration only**: Nodes never actually deleted, just ignored
- ❌ **Memory leak**: DAG grows unbounded in memory
- ❌ **No hard TTL**: Old nodes consume memory forever

### 3. Memory State on System Kill/Restart

**Status: ❌ CRITICAL DATA LOSS SCENARIOS**

**Redis State:**
- ✅ **TTL preserved**: Redis maintains TTL across restarts
- ✅ **Data persistence**: Redis RDB/AOF persistence enabled

**Memory DAG State:**
```python
# From memory_dag.py - JSON persistence
def save_json(self, path: str | Path) -> None:
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")

@classmethod
def load_json(cls, path: str | Path) -> "MemoryDag":
    in_path = Path(path)
    if not in_path.exists():
        return cls()  # ❌ Returns empty DAG if file missing
```

**Critical Issues:**
- ❌ **Manual persistence**: No automatic saves during operation
- ❌ **Data loss window**: Changes lost between manual saves
- ❌ **No atomic writes**: JSON write can be interrupted, corrupting file
- ❌ **No backup strategy**: Single point of failure

**Usage Pattern:**
```python
# From run_research_factory.py - Manual save after operation
memory_dag = MemoryDag.load_json(dag_path)
# ... do work ...
memory_dag.save_json(dag_path)  # ❌ Only saved at end
```

---

## **Memory Leak Risks and State Corruption Scenarios**

### **Critical Memory Leaks:**

1. **Unbounded Memory DAG Growth**
   ```python
   # DAG nodes never deleted, only soft-expired via provenance decay
   # Memory usage grows linearly with system runtime
   # Risk: OOM after extended operation
   ```

2. **Graphiti Episode Accumulation**
   ```python
   # No TTL or cleanup for Neo4j episodes
   # Graph size grows indefinitely
   # Risk: Query performance degradation, storage exhaustion
   ```

3. **AgentMemoryRecorder Client Leaks**
   ```python
   # Lazy-initialized clients never cleaned up
   # Each agent creates persistent connections
   # Risk: Connection pool exhaustion
   ```

### **State Corruption Scenarios:**

1. **Async/Sync Deadlock**
   ```python
   # asyncio.run() called from sync context can deadlock
   # Scenario: Agent calls remember() from async context
   # Result: Process hangs, memory state becomes inconsistent
   ```

2. **Partial Write Failures**
   ```python
   # Mem0 write succeeds, Graphiti write fails
   # Result: Inconsistent state between fast and temporal memory
   # No rollback mechanism exists
   ```

3. **JSON Corruption During Save**
   ```python
   # Process killed during memory_dag.save_json()
   # Result: Corrupted JSON file, entire DAG lost on restart
   # No atomic write protection
   ```

4. **Redis Connection Loss**
   ```python
   # Redis connection drops during setex() call
   # Result: TTL not set, data persists indefinitely
   # No retry or verification mechanism
   ```

### **Race Condition Risks:**

1. **Concurrent DAG Modification**
   ```python
   # Multiple threads can modify MemoryDag simultaneously
   # No locking mechanism exists
   # Result: Corrupted node/edge relationships
   ```

2. **Episode Name Collisions**
   ```python
   # Episode names use int(time.time())
   # High-frequency operations can generate same timestamp
   # Result: Episodes overwrite each other
   ```

---

## **Recommendations for Critical Fixes**

### **Immediate (System-Breaking Issues):**

1. **Fix Async/Sync Mismatch**
   ```python
   class AgentMemory:
       async def remember_async(self, text: str, important: bool = False) -> None:
           await self.fast.add_async(text, user_id=self.agent_id)
           if important:
               await self.graph.add_episode(...)
       
       def remember(self, text: str, important: bool = False) -> None:
           # Queue for background processing instead of blocking
           self._memory_queue.put((text, important))
   ```

2. **Implement Atomic Persistence**
   ```python
   def save_json_atomic(self, path: str | Path) -> None:
       temp_path = Path(f"{path}.tmp")
       temp_path.write_text(json.dumps(self.to_dict(), indent=2))
       temp_path.rename(path)  # Atomic on POSIX systems
   ```

3. **Add TTL to Memory DAG**
   ```python
   def cleanup_expired_nodes(self, max_age_hours: int = 72) -> int:
       cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
       expired = [n for n in self._nodes.values() if n.created_at < cutoff]
       for node in expired:
           self._remove_node(node.node_id)
       return len(expired)
   ```

### **High Priority (Data Loss Prevention):**

4. **Implement Background Persistence**
   ```python
   class PersistentMemoryDag(MemoryDag):
       def __init__(self, path: Path, save_interval: int = 300):
           super().__init__()
           self._path = path
           self._save_timer = threading.Timer(save_interval, self._auto_save)
           self._save_timer.start()
   ```

5. **Add Error Handling and Logging**
   ```python
   def remember(self, text: str, important: bool = False) -> None:
       try:
           self._client.remember(text, important=important)
           logger.info(f"Memory stored: {text[:50]}...")
       except Exception as e:
           logger.error(f"Memory storage failed: {e}")
           # Store in fallback queue for retry
           self._failed_memories.append((text, important, datetime.now()))
   ```

6. **Implement Connection Pooling**
   ```python
   class MemoryConnectionPool:
       def __init__(self, max_connections: int = 10):
           self._pool = asyncio.Queue(maxsize=max_connections)
           self._connections = {}
   ```

### **Medium Priority (Performance and Reliability):**

7. **Add Duplicate Detection**
   ```python
   def add_episode_deduplicated(self, episode_body: str, **kwargs) -> str:
       content_hash = hashlib.sha256(episode_body.encode()).hexdigest()[:16]
       episode_name = f"{self.agent_id}_{content_hash}"
       # Check if episode already exists before creating
   ```

8. **Implement Proper TTL Tiers**
   ```python
   class TieredCache:
       def __init__(self):
           self.heartbeat_cache = TTLCache(maxsize=1000, ttl=600)      # 10min
           self.decision_cache = TTLCache(maxsize=10000, ttl=259200)   # 72h
           self.research_cache = TTLCache(maxsize=50000, ttl=259200)   # 72h
   ```

---

## **Conclusion**

The CryptoSwarms memory subsystem has a sophisticated conceptual design but **dangerous implementation gaps** that pose significant risks to system reliability and data integrity. The most critical issues are:

1. **Async/sync mismatches** that can cause deadlocks
2. **Unbounded memory growth** in DAG and Neo4j
3. **Manual persistence** with data loss windows
4. **Silent failure modes** throughout the memory stack

**Priority Actions:**
1. Fix the async/sync deadlock in `AgentMemory.remember()`
2. Implement atomic persistence for Memory DAG
3. Add proper TTL cleanup for all memory tiers
4. Replace silent exception handling with proper error logging

Without these fixes, the system will experience memory leaks, data corruption, and catastrophic failures in production environments.

**Final Score: 4/10** - Conceptually advanced but implementation is dangerously incomplete.