from sqlalchemy import BigInteger, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from db.models.base import Base, IdMixin, TimestampMixin

class MessageMapping(Base, IdMixin, TimestampMixin):
    __tablename__ = "message_mappings"
    
    userId: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    userChatId: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False
    )
    
    userMessageId: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        index=True
    )

    userLastEditMessageId: Mapped[int] = mapped_column(
        BigInteger,
        nullable=True,
        index=True
    )
    
    channelChatId: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False
    )
    
    channelMessageId: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        index=True
    )
    
    isDeleted: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )
    
    user: Mapped["User"] = relationship("User", backref="messages")    
    def __repr__(self) -> str:
        return (
            f"<MessageMapping(id={self.id}, "
            f"userMessageId={self.userMessageId}, "
            f"channelMessageId={self.channelMessageId})>"
        )
    