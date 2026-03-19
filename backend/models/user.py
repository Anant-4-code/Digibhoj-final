from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum as SAEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.database import Base
import enum

class UserRole(str, enum.Enum):
    customer = "customer"
    provider = "provider"
    delivery = "delivery"
    admin = "admin"

class UserStatus(str, enum.Enum):
    active = "active"
    blocked = "blocked"
    pending = "pending"

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(SAEnum(UserRole), default=UserRole.customer)
    status = Column(SAEnum(UserStatus), default=UserStatus.active)
    created_at = Column(DateTime, server_default=func.now())

    customer = relationship("Customer", back_populates="user", uselist=False, cascade="all, delete-orphan")
    provider = relationship("Provider", back_populates="user", uselist=False, cascade="all, delete-orphan")
    delivery_agent = relationship("DeliveryAgent", back_populates="user", uselist=False, cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")
