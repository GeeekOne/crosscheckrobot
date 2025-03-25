from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from database.models import Base

DATABASE_URL = "sqlite+aiosqlite:///db.sqlite3"

engine = create_async_engine(DATABASE_URL, echo=True)
async_session = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def close_db():
    await engine.dispose()
