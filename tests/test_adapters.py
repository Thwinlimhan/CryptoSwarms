from cryptoswarms import PostgresSqlExecutor, RedisKeyValueStore


class FakeRedis:
    def __init__(self) -> None:
        self.data = {"bytes": b"hello"}
        self.ttl_calls = []

    def set(self, key: str, value: str) -> None:
        self.data[key] = value

    def setex(self, key: str, ttl_seconds: int, value: str) -> None:
        self.ttl_calls.append((key, ttl_seconds, value))
        self.data[key] = value

    def get(self, key: str):
        return self.data.get(key)


class FakeCursor:
    def __init__(self, conn) -> None:
        self.conn = conn

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql, params):
        self.conn.calls.append((sql, params))

    def fetchall(self):
        return [("scanner", "qwen", 1.2)]


class FakeConnection:
    def __init__(self) -> None:
        self.calls = []
        self.commits = 0

    def cursor(self):
        return FakeCursor(self)

    def commit(self):
        self.commits += 1


def test_redis_adapter_handles_bytes_strings_and_ttl_set():
    backend = FakeRedis()
    store = RedisKeyValueStore(backend)
    assert store.get("bytes") == "hello"
    store.set("plain", "world")
    store.setex("ttl_key", 30, "v")
    assert store.get("plain") == "world"
    assert backend.ttl_calls[0] == ("ttl_key", 30, "v")


def test_postgres_executor_execute_and_fetchall():
    conn = FakeConnection()
    db = PostgresSqlExecutor(conn)

    db.execute("SELECT 1", ())
    rows = db.fetchall("SELECT 2", ())

    assert conn.commits == 1
    assert rows[0][0] == "scanner"
    assert conn.calls[0][0] == "SELECT 1"
