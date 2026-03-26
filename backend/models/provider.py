from sqlalchemy import Column, Integer, String, ForeignKey, Float, Text, Boolean, DateTime, Enum as SAEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.database import Base
import enum

class VerificationStatus(str, enum.Enum):
    pending = "pending"
    verified = "verified"
    blocked = "blocked"

class DocumentType(str, enum.Enum):
    aadhaar = "aadhaar"
    fssai = "fssai"
    business_license = "business_license"

class DocumentStatus(str, enum.Enum):
    pending = "pending"
    verified = "verified"
    rejected = "rejected"

class Provider(Base):
    __tablename__ = "providers"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    mess_name = Column(String, nullable=False)
    cuisine_type = Column(String)
    location = Column(String)
    phone = Column(String)
    description = Column(Text)
    image_url = Column(String, default="/assets/images/provider-default.jpg")
    operating_hours = Column(String, default="8 AM – 9 PM")
    verification_status = Column(SAEnum(VerificationStatus), default=VerificationStatus.pending)
    rating = Column(Float, default=0.0)
    total_reviews = Column(Integer, default=0)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    vacation_mode = Column(Boolean, default=False)
    auto_accept_orders = Column(Boolean, default=False)
    email_notifications = Column(Boolean, default=True)
    sms_notifications = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="provider")
    meals = relationship("Meal", back_populates="provider", cascade="all, delete")
    subscription_plans = relationship("SubscriptionPlan", back_populates="provider", cascade="all, delete")
    orders = relationship("Order", back_populates="provider")
    reviews = relationship("Review", back_populates="provider")
    documents = relationship("ProviderDocument", back_populates="provider", cascade="all, delete-orphan")
    bank_details = relationship("ProviderBank", back_populates="provider", uselist=False, cascade="all, delete-orphan")

class ProviderDocument(Base):
    __tablename__ = "provider_documents"
    id = Column(Integer, primary_key=True, index=True)
    provider_id = Column(Integer, ForeignKey("providers.id", ondelete="CASCADE"))
    document_type = Column(SAEnum(DocumentType), nullable=False)
    file_url = Column(String, nullable=False)
    status = Column(SAEnum(DocumentStatus), default=DocumentStatus.pending)
    admin_note = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    provider = relationship("Provider", back_populates="documents")

class ProviderBank(Base):
    __tablename__ = "provider_bank"
    id = Column(Integer, primary_key=True, index=True)
    provider_id = Column(Integer, ForeignKey("providers.id", ondelete="CASCADE"), unique=True)
    account_name = Column(String, nullable=False)
    account_number = Column(String, nullable=False)
    ifsc_code = Column(String, nullable=False)
    bank_name = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    provider = relationship("Provider", back_populates="bank_details", uselist=False)
