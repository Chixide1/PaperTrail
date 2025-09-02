from datetime import datetime
from sqlalchemy import DateTime, create_engine
from sqlalchemy.orm import sessionmaker, MappedAsDataclass, DeclarativeBase
from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

SQLALCHEMY_DATABASE_URL = "sqlite:///./db.sqlite"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
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