from sqlalchemy import Column, String, Integer, Text, BigInteger
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine, AsyncAttrs
from sqlalchemy.orm import DeclarativeBase


# Базовый класс
class Base(AsyncAttrs, DeclarativeBase):
    pass

# Модель для постов
class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(100), nullable=False) # Название поста
    content = Column(Text, nullable=False) # Содержание поста
    media_type = Column(String(20), nullable=True) # Тип медиа (текст, фото, видео)
    media_id = Column(String(200), nullable=True) # ID медиа