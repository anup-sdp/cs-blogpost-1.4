# reset_db.py
# This script drops and recreates all tables in the database based on current SQLAlchemy models.
# if not using alembic, this is a quick way to reset the database schema during development.

import asyncio
from database import engine, Base
import models  # Ensure models are imported to register them with Base

async def reset_database():
    print("Connecting to Neon PostgreSQL (Async)...")
    
    async with engine.begin() as conn:
        # We use run_sync to execute the synchronous drop/create methods
        print("Dropping all tables...")
        await conn.run_sync(Base.metadata.drop_all)
        
        print("Recreating all tables...")
        await conn.run_sync(Base.metadata.create_all)
        
    print("Database has been successfully reset!")

if __name__ == "__main__":
    # Run the async function using asyncio
    asyncio.run(reset_database())


"""
activate virtual environment is active, and run:
python reset_db.py

or, uv run reset_db.py
"""