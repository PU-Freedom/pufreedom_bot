from sqlalchemy import BigInteger, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from db.models.base import Base, IdMixin, TimestampMixin


class ChannelThreadMapping(Base, IdMixin, TimestampMixin):
    __tablename__ = "channel_thread_mappings"
    __table_args__ = (
        UniqueConstraint("channelPostId", name="uq_channel_thread_channelPostId"),
    )

    channelPostId: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    groupThreadId: Mapped[int] = mapped_column(BigInteger, nullable=False)

    def __repr__(self) -> str:
        return (
            f"<ChannelThreadMapping(channelPostId={self.channelPostId}, "
            f"groupThreadId={self.groupThreadId})>"
        )
