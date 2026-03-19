from sqlalchemy import Column, Integer, String, ForeignKey, Float, Text, Boolean, DateTime, Enum as SAEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.database import Base
import enum

class AgentStatus(str, enum.Enum):
    online = "online"
    offline = "offline"
    busy = "busy"

class DeliveryVerification(str, enum.Enum):
    pending = "pending"
    verified = "verified"
    blocked = "blocked"

class DeliveryAgent(Base):
    __tablename__ = "delivery_agents"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    phone = Column(String)
    vehicle_type = Column(String, default="Bike")
    license_number = Column(String)
    service_area = Column(String)
    verification_status = Column(SAEnum(DeliveryVerification), default=DeliveryVerification.pending)
    availability = Column(SAEnum(AgentStatus), default=AgentStatus.offline)
    total_earnings = Column(Float, default=0.0)
    current_lat = Column(Float, nullable=True)
    current_lng = Column(Float, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="delivery_agent")
    assignments = relationship("DeliveryAssignment", back_populates="agent")
