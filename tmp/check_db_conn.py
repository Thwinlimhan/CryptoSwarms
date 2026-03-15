import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def test_conn():
    user = os.getenv("TIMESCALEDB_USER")
    password = os.getenv("TIMESCALEDB_PASSWORD")
    database = os.getenv("TIMESCALEDB_DB")
    host = os.getenv("TIMESCALEDB_HOST")
    port = os.getenv("TIMESCALEDB_PORT")
    
    print(f"Testing connection to {user}@{host}:{port}/{database}...")
    try:
        conn = await asyncpg.connect(user=user, password=password, database=database, host=host, port=port)
        print("Success!")
        await conn.close()
    except Exception as e:
        print(f"Failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_conn())
