from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean, 
    Numeric, ForeignKey, JSON, Date, BigInteger, Index,
    UniqueConstraint, CheckConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from core.database import Base

class CarWash(Base):
    __tablename__ = "carwashes"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    address = Column(Text)
    phone = Column(String(20))
    working_hours = Column(JSON, default={})
    slot_duration = Column(Integer, default=60)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    users = relationship("User", back_populates="car_wash")
    services = relationship("Service", back_populates="car_wash")
    appointments = relationship("Appointment", back_populates="car_wash")

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    car_wash_id = Column(Integer, ForeignKey("carwashes.id"))
    role = Column(String(50), nullable=False, default="client")
    full_name = Column(String(255))
    username = Column(String(255))
    phone = Column(String(20))
    balance = Column(Numeric(10, 2), default=0)
    is_blocked = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    car_wash = relationship("CarWash", back_populates="users")
    appointments = relationship("Appointment", back_populates="user")
    subscriptions = relationship("Subscription", back_populates="user")
    
    __table_args__ = (
        Index("ix_users_telegram_id", "telegram_id"),
        Index("ix_users_role", "role"),
    )

class Service(Base):
    __tablename__ = "services"
    
    id = Column(Integer, primary_key=True)
    car_wash_id = Column(Integer, ForeignKey("carwashes.id"))
    name = Column(String(255), nullable=False)
    description = Column(Text)
    price = Column(Numeric(10, 2), nullable=False)
    duration = Column(Integer, nullable=False)  # minutes
    is_active = Column(Boolean, default=True)
    car_category = Column(String(50), nullable=False, default="sedan")
    max_discount_percent = Column(Integer, nullable=False, default=0)
    
    # Relationships
    car_wash = relationship("CarWash", back_populates="services")
    appointments = relationship("Appointment", back_populates="service")

class Appointment(Base):
    __tablename__ = "appointments"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    service_id = Column(Integer, ForeignKey("services.id"))
    car_wash_id = Column(Integer, ForeignKey("carwashes.id"))
    appointment_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    status = Column(String(50), nullable=False, default="confirmed")
    payment_method = Column(String(50))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))
    
    # Relationships
    user = relationship("User", back_populates="appointments")
    service = relationship("Service", back_populates="appointments")
    car_wash = relationship("CarWash", back_populates="appointments")
    
    __table_args__ = (
        Index("ix_appointments_time", "appointment_time"),
        Index("ix_appointments_status", "status"),
    )

class Subscription(Base):
    __tablename__ = "subscriptions"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    car_wash_id = Column(Integer, ForeignKey("carwashes.id"))
    name = Column(String(255), nullable=False)
    total_washes = Column(Integer, nullable=False)
    remaining_washes = Column(Integer, nullable=False)
    purchase_price = Column(Numeric(10, 2), nullable=False)
    valid_until = Column(Date)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="subscriptions")

class Transaction(Base):
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    car_wash_id = Column(Integer, ForeignKey("carwashes.id"))
    amount = Column(Numeric(10, 2), nullable=False)
    type = Column(String(50), nullable=False)  # replenishment, subscription_purchase, service_payment
    status = Column(String(50), nullable=False, default="pending")
    payment_method = Column(String(50))
    admin_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    approved_at = Column(DateTime(timezone=True))
    
    __table_args__ = (
        Index("ix_transactions_status", "status"),
        Index("ix_transactions_created", "created_at"),
    )
