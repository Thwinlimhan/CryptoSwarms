import asyncio
import asyncpg
from api.settings import settings

async def check_tables():
    dsn = f"postgres://{settings.timescaledb_user}:{settings.timescaledb_password}@{settings.timescaledb_host}:{settings.timescaledb_port}/{settings.timescaledb_db}"
    print(f"Connecting to {dsn}...")
    conn = await asyncpg.connect(dsn)
    try:
        rows = await conn.fetch("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
        print("Tables in public schema:")
        for r in rows:
            print(f"- {r['table_name']}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(check_tables())
