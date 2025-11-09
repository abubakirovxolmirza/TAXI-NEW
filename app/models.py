from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Numeric, Enum as SQLEnum, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
from decimal import Decimal
import enum


class UserRole(str, enum.Enum):
    USER = "user"
    DRIVER = "driver"
    ADMIN = "admin"
    SUPERADMIN = "superadmin"


class Language(str, enum.Enum):
    UZ_LATIN = "uz_latin"
    UZ_CYRILLIC = "uz_cyrillic"
    RUSSIAN = "russian"


class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ApplicationStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ItemType(str, enum.Enum):
    DOCUMENT = "document"
    BOX = "box"
    LUGGAGE = "luggage"
    VALUABLE = "valuable"
    OTHER = "other"


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    telephone = Column(String(20), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(SQLEnum(UserRole), default=UserRole.USER, nullable=False)
    language = Column(SQLEnum(Language), default=Language.UZ_LATIN, nullable=False)
    profile_picture = Column(String(255), nullable=True)
    telegram_chat_id = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    driver_profile = relationship("Driver", back_populates="user", uselist=False)
    taxi_orders = relationship("TaxiOrder", back_populates="user", foreign_keys="TaxiOrder.user_id")
    delivery_orders = relationship("DeliveryOrder", back_populates="user", foreign_keys="DeliveryOrder.user_id")
    ratings_given = relationship("Rating", back_populates="user", foreign_keys="Rating.user_id")
    driver_application = relationship("DriverApplication", back_populates="user", foreign_keys="DriverApplication.user_id", uselist=False)


class Driver(Base):
    __tablename__ = "drivers"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    full_name = Column(String(100), nullable=False)
    car_model = Column(String(100), nullable=False)
    car_number = Column(String(20), nullable=False)
    license_photo = Column(String(255), nullable=False)
    rating = Column(Numeric(3, 2), default=0.00)
    balance = Column(Numeric(10, 2), default=0.00)
    is_blocked = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="driver_profile")
    taxi_orders = relationship("TaxiOrder", back_populates="driver", foreign_keys="TaxiOrder.driver_id")
    delivery_orders = relationship("DeliveryOrder", back_populates="driver", foreign_keys="DeliveryOrder.driver_id")
    ratings_received = relationship("Rating", back_populates="driver", foreign_keys="Rating.driver_id")
    balance_transactions = relationship("BalanceTransaction", back_populates="driver")


class Region(Base):
    __tablename__ = "regions"
    
    id = Column(Integer, primary_key=True, index=True)
    name_uz_latin = Column(String(100), nullable=False)
    name_uz_cyrillic = Column(String(100), nullable=False)
    name_russian = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    districts = relationship("District", back_populates="region")


class District(Base):
    __tablename__ = "districts"
    
    id = Column(Integer, primary_key=True, index=True)
    region_id = Column(Integer, ForeignKey("regions.id"), nullable=False)
    name_uz_latin = Column(String(100), nullable=False)
    name_uz_cyrillic = Column(String(100), nullable=False)
    name_russian = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    region = relationship("Region", back_populates="districts")


class TaxiOrder(Base):
    __tablename__ = "taxi_orders"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    driver_id = Column(Integer, ForeignKey("drivers.id"), nullable=True)
    username = Column(String(100), nullable=False)
    telephone = Column(String(20), nullable=False)
    from_region_id = Column(Integer, ForeignKey("regions.id"), nullable=False)
    from_district_id = Column(Integer, ForeignKey("districts.id"), nullable=False)
    to_region_id = Column(Integer, ForeignKey("regions.id"), nullable=False)
    to_district_id = Column(Integer, ForeignKey("districts.id"), nullable=False)
    pickup_latitude = Column(Numeric(10, 8), nullable=True)  # Client's pickup latitude
    pickup_longitude = Column(Numeric(11, 8), nullable=True)  # Client's pickup longitude
    pickup_address = Column(Text, nullable=True)  # Optional address description
    passengers = Column(Integer, nullable=False)  # 1, 2, 3, 4
    is_mail_delivery = Column(Boolean, default=False, nullable=False)  # True if sending package/item instead of passenger
    date = Column(String(10), nullable=False)  # dd.mm.yyyy
    time_start = Column(String(5), nullable=False)  # HH:MM
    time_end = Column(String(5), nullable=False)  # HH:MM
    scheduled_datetime = Column(DateTime(timezone=True), nullable=True)  # Scheduled pickup datetime
    price = Column(Numeric(10, 2), nullable=False)
    service_fee = Column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)  # 8% platform fee
    driver_earnings = Column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)  # Driver's portion after fee
    note = Column(Text, nullable=True)
    status = Column(SQLEnum(OrderStatus), default=OrderStatus.PENDING, nullable=False)
    cancellation_reason = Column(Text, nullable=True)
    accepted_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="taxi_orders", foreign_keys=[user_id])
    driver = relationship("Driver", back_populates="taxi_orders", foreign_keys=[driver_id])
    from_region = relationship("Region", foreign_keys=[from_region_id])
    from_district = relationship("District", foreign_keys=[from_district_id])
    to_region = relationship("Region", foreign_keys=[to_region_id])
    to_district = relationship("District", foreign_keys=[to_district_id])
    rating = relationship("Rating", back_populates="taxi_order", uselist=False)


class DeliveryOrder(Base):
    __tablename__ = "delivery_orders"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    driver_id = Column(Integer, ForeignKey("drivers.id"), nullable=True)
    username = Column(String(100), nullable=False)
    sender_telephone = Column(String(20), nullable=False)
    receiver_telephone = Column(String(20), nullable=False)
    from_region_id = Column(Integer, ForeignKey("regions.id"), nullable=False)
    from_district_id = Column(Integer, ForeignKey("districts.id"), nullable=False)
    to_region_id = Column(Integer, ForeignKey("regions.id"), nullable=False)
    to_district_id = Column(Integer, ForeignKey("districts.id"), nullable=False)
    pickup_latitude = Column(Numeric(10, 8), nullable=True)  # Sender's pickup latitude
    pickup_longitude = Column(Numeric(11, 8), nullable=True)  # Sender's pickup longitude
    pickup_address = Column(Text, nullable=True)  # Sender's address
    dropoff_latitude = Column(Numeric(10, 8), nullable=True)  # Receiver's drop-off latitude
    dropoff_longitude = Column(Numeric(11, 8), nullable=True)  # Receiver's drop-off longitude
    dropoff_address = Column(Text, nullable=True)  # Receiver's address
    item_type = Column(SQLEnum(ItemType), nullable=False)
    date = Column(String(10), nullable=False)  # dd.mm.yyyy
    time_start = Column(String(5), nullable=False)  # HH:MM
    time_end = Column(String(5), nullable=False)  # HH:MM
    scheduled_datetime = Column(DateTime(timezone=True), nullable=True)  # Scheduled pickup datetime
    price = Column(Numeric(10, 2), nullable=False)
    service_fee = Column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)  # 8% platform fee
    driver_earnings = Column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)  # Driver's portion after fee
    note = Column(Text, nullable=True)
    status = Column(SQLEnum(OrderStatus), default=OrderStatus.PENDING, nullable=False)
    cancellation_reason = Column(Text, nullable=True)
    accepted_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="delivery_orders", foreign_keys=[user_id])
    driver = relationship("Driver", back_populates="delivery_orders", foreign_keys=[driver_id])
    from_region = relationship("Region", foreign_keys=[from_region_id])
    from_district = relationship("District", foreign_keys=[from_district_id])
    to_region = relationship("Region", foreign_keys=[to_region_id])
    to_district = relationship("District", foreign_keys=[to_district_id])
    rating = relationship("Rating", back_populates="delivery_order", uselist=False)


class Rating(Base):
    __tablename__ = "ratings"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    driver_id = Column(Integer, ForeignKey("drivers.id"), nullable=False)
    taxi_order_id = Column(Integer, ForeignKey("taxi_orders.id"), nullable=True)
    delivery_order_id = Column(Integer, ForeignKey("delivery_orders.id"), nullable=True)
    rating = Column(Integer, nullable=False)  # 1-5
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="ratings_given", foreign_keys=[user_id])
    driver = relationship("Driver", back_populates="ratings_received", foreign_keys=[driver_id])
    taxi_order = relationship("TaxiOrder", back_populates="rating", foreign_keys=[taxi_order_id])
    delivery_order = relationship("DeliveryOrder", back_populates="rating", foreign_keys=[delivery_order_id])


class DriverApplication(Base):
    __tablename__ = "driver_applications"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    full_name = Column(String(100), nullable=False)
    telephone = Column(String(20), nullable=False)
    car_model = Column(String(100), nullable=False)
    car_number = Column(String(20), nullable=False)
    license_photo = Column(String(255), nullable=False)
    status = Column(SQLEnum(ApplicationStatus), default=ApplicationStatus.PENDING, nullable=False)
    rejection_reason = Column(Text, nullable=True)
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="driver_application", foreign_keys=[user_id])
    reviewer = relationship("User", foreign_keys=[reviewed_by])


class Pricing(Base):
    __tablename__ = "pricing"
    
    id = Column(Integer, primary_key=True, index=True)
    from_region_id = Column(Integer, ForeignKey("regions.id"), nullable=False)
    to_region_id = Column(Integer, ForeignKey("regions.id"), nullable=False)
    service_type = Column(String(20), nullable=False)  # "taxi" or "delivery"
    base_price = Column(Numeric(10, 2), nullable=False)
    discount_1_passenger = Column(Numeric(5, 2), default=0.00)  # percentage
    discount_2_passengers = Column(Numeric(5, 2), default=0.00)
    discount_3_passengers = Column(Numeric(5, 2), default=0.00)
    discount_full_car = Column(Numeric(5, 2), default=0.00)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    from_region = relationship("Region", foreign_keys=[from_region_id])
    to_region = relationship("Region", foreign_keys=[to_region_id])


class BalanceTransaction(Base):
    __tablename__ = "balance_transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    driver_id = Column(Integer, ForeignKey("drivers.id"), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    transaction_type = Column(String(20), nullable=False)  # "credit", "debit", "refund"
    description = Column(Text, nullable=True)
    admin_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    driver = relationship("Driver", back_populates="balance_transactions")
    admin = relationship("User", foreign_keys=[admin_id])


class Notification(Base):
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    driver_id = Column(Integer, ForeignKey("drivers.id"), nullable=True)
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    notification_type = Column(String(50), nullable=False)
    is_read = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    driver = relationship("Driver", foreign_keys=[driver_id])


class Feedback(Base):
    __tablename__ = "feedback"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    telegram_chat_id = Column(String(50), nullable=True)
    message = Column(Text, nullable=False)
    is_reviewed = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])


class SystemSettings(Base):
    __tablename__ = "system_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    setting_key = Column(String(100), unique=True, nullable=False, index=True)
    setting_value = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    admin = relationship("User", foreign_keys=[updated_by])
