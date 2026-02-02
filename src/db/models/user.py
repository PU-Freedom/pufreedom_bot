from sqlalchemy import BigInteger, String, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from db.models.base import Base, IdMixin, TimestampMixin

class User(Base, IdMixin, TimestampMixin):
    __tablename__ = "users"
    
    telegramId: Mapped[int] = mapped_column(
        BigInteger,
        unique=True,
        nullable=False,
        index=True
    )
    
    username: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )
    
    firstName: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    
    lastName: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )
    
    isBanned: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )

    isAdmin: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )
    
    lastActiveAt: Mapped[datetime] = mapped_column(
        nullable=False,
        server_default=func.now()
    )
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, telegramId={self.telegramId}, username={self.username})>"
    