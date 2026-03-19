from sqlalchemy import Column, Integer, ForeignKey, Float, Text, DateTime, Enum as SAEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.database import Base
import enum

class DeliveryAssignmentStatus(str, enum.Enum):
    assigned = "assigned"
    accepted = "accepted"
    picked_up = "picked_up"
    out_for_delivery = "out_for_delivery"
    completed = "completed"
    rejected = "rejected"

class DeliveryAssignment(Base):
    __tablename__ = "delivery_assignments"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), unique=True)
    agent_id = Column(Integer, ForeignKey("delivery_agents.id"))
    pickup_location = Column(Text)
    drop_location = Column(Text)
    status = Column(SAEnum(DeliveryAssignmentStatus), default=DeliveryAssignmentStatus.assigned)
    assigned_at = Column(DateTime, server_default=func.now())

    order = relationship("Order", back_populates="assignment")
    agent = relationship("DeliveryAgent", back_populates="assignments")
