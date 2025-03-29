from sqlalchemy import Column, DateTime, String, Integer, Text, BigInteger, Boolean
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func


# Базовый класс
class Base(AsyncAttrs, DeclarativeBase):
    pass

class GroupSettings(Base):
    __tablename__ = "group_settings"
    __table_args__ = {"schema": "public"}

    group_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    admin_ids: Mapped[str] = mapped_column(String, nullable=False)
    approve_requests: Mapped[bool] = mapped_column(Boolean, default=False)
    delete_join_leave_messages: Mapped[bool] = mapped_column(Boolean, default=False)
    captcha_timeout: Mapped[int] = mapped_column(Integer, default=5)

    # def __repr__(self):
    #     return (f"<GroupSettings(group_id={self.group_id}, admin_ids={self.admin_ids}, "
    #             f"approve_requests={self.approve_requests}, "
    #             f"delete_join_leave_messages={self.delete_join_leave_messages}, "
    #             f"captcha_timout={self.captcha_timeout})>")


class AdminSession(Base):
    __tablename__ = 'admin_sessions'
    __table_args__ = {"schema": "public"}

    admin_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    group_id: Mapped[int] = mapped_column(BigInteger, nullable=False)


class PendingRequest(Base):
    __tablename__ = "pending_requests"
    __table_args__ = {"schema": "public"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    message_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime, default=func.now())