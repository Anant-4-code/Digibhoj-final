from sqlalchemy import Column, Integer, ForeignKey, Text, DateTime, String, Enum as SAEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.database import Base
import enum

class NotificationType(str, enum.Enum):
    order_update = "order_update"
    delivery_update = "delivery_update"
    system_alert = "system_alert"

class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    message = Column(Text)
    ntype = Column(SAEnum(NotificationType), default=NotificationType.system_alert)
    is_read = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="notifications")
