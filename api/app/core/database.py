from datetime import datetime
from sqlalchemy import DateTime, create_engine
from sqlalchemy.orm import sessionmaker, MappedAsDataclass, DeclarativeBase
from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.core.config import settings

engine = create_engine(
    settings.SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(MappedAsDataclass, DeclarativeBase):
    """subclasses will be converted to dataclasses"""

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, init=False, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String, unique=True, index=True)
    hashed_password: Mapped[str]
    last_password_change: Mapped[datetime] = mapped_column(DateTime)

class Message(Base):
    __tablename__ = "message_store"

    id: Mapped[int] = mapped_column(Integer, init=False, primary_key=True, index=True)
    session_id: Mapped[str] = mapped_column(Text, index=True)
    message: Mapped[str] = mapped_column(Text)
    # type: Mapped[str]  # 'human', 'ai', or 'system'
    # created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)