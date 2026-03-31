from sqlalchemy import BigInteger, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from db.models.base import Base, IdMixin, TimestampMixin

class CommentMapping(Base, IdMixin, TimestampMixin):
    __tablename__ = "comment_mappings"

    userId: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    userChatId: Mapped[int] = mapped_column(BigInteger, nullable=False)

    userMessageId: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)

    groupChatId: Mapped[int] = mapped_column(BigInteger, nullable=False)

    groupMessageId: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)

    channelPostId: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)

    isDeleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user: Mapped["User"] = relationship("User", backref="comments")

    def __repr__(self) -> str:
        return (
            f"<CommentMapping(id={self.id}, "
            f"userId={self.userId}, "
            f"groupMessageId={self.groupMessageId}, "
            f"channelPostId={self.channelPostId})>"
        )
