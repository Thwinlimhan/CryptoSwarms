import asyncio
import asyncpg
import os
from api.settings import settings

async def apply_schemas():
    dsn = f"postgres://{settings.timescaledb_user}:{settings.timescaledb_password}@{settings.timescaledb_host}:{settings.timescaledb_port}/{settings.timescaledb_db}"
    print(f"Connecting to {dsn}...")
    conn = await asyncpg.connect(dsn)
    
    schema_dir = "c:/Users/thwin/Desktop/CryptoSwarms/data/schemas"
    schemas = ["002_decisions.sql", "003_research.sql"]
    
    try:
        for schema_file in schemas:
            path = os.path.join(schema_dir, schema_file)
            print(f"Applying {schema_file}...")
            if not os.path.exists(path):
                print(f"File {path} not found!")
                continue
                
            with open(path, "r") as f:
                sql = f.read()
            
            # TimescaleDB hypertable creation might throw notice if already exists,
            # but CREATE TABLE IF NOT EXISTS is safe.
            # We split by semicolon to run individually if needed, but asyncpg.execute handles multiple statements.
            try:
                await conn.execute(sql)
                print(f"Successfully applied {schema_file}")
            except Exception as e:
                print(f"Error applying {schema_file}: {e}")
                
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(apply_schemas())
