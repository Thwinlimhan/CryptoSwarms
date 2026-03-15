import asyncpg
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

async def test_conn():
    user = os.getenv("TIMESCALEDB_USER", "swarm")
    password = os.getenv("TIMESCALEDB_PASSWORD", "swarm")
    host = os.getenv("TIMESCALEDB_HOST", "127.0.0.1")
    port = os.getenv("TIMESCALEDB_PORT", "5432")
    db = os.getenv("TIMESCALEDB_DB", "swarm_db")
    
    dsn = f"postgresql://{user}:{password}@{host}:{port}/{db}"
    print(f"Connecting to: {dsn}")
    try:
        conn = await asyncpg.connect(dsn)
        print("Connection successful!")
        await conn.close()
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_conn())
