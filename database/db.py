from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from database.models import Base
from config import load_config


def create_engine(db_url: str):
    return create_async_engine(db_url, echo=True)

config = load_config('.env')
engine = create_engine(config.tg_bot.db_url)

def create_session(engine):
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async_session = create_session(engine)

async def init_db(engine):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def close_db(engine):
    await engine.dispose()
