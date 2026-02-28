from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Numeric, Enum as SQLEnum, Text, BigInteger, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
from decimal import Decimal
import enum
import uuid


class UserRole(str, enum.Enum):
    USER = "user"
    DRIVER = "driver"
    ADMIN = "admin"
    SUPERADMIN = "superadmin"


class Language(str, enum.Enum):
    UZ_LATIN = "uz_latin"
    UZ_CYRILLIC = "uz_cyrillic"
    RUSSIAN = "russian"


class Gender(str, enum.Enum):
    MALE = "male"
    FEMALE = "female"
    BOTH = "both"  # Female and male


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


class SeatType(str, enum.Enum):
    FRONT = "front"
    BACK = "back"


class Tariff(str, enum.Enum):
    STANDARD = "standard"
    COMFORT = "comfort"
    COMFORT_PLUS = "comfort_plus"
    BUSINESS = "business"


class TopUpStatus(str, enum.Enum):
    CREATED = "CREATED"
    PREPARED = "PREPARED"
    PAID = "PAID"
    FAILED = "FAILED"
    CANCELED = "CANCELED"


class DevicePlatform(str, enum.Enum):
    ANDROID = "android"
    IOS = "ios"
    WEB = "web"


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    telephone = Column(String(20), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(SQLEnum(UserRole, values_callable=lambda obj: [e.value for e in obj]), default=UserRole.USER, nullable=False)
    language = Column(SQLEnum(Language, values_callable=lambda obj: [e.value for e in obj]), default=Language.UZ_LATIN, nullable=False)
    profile_picture = Column(String(255), nullable=True)
    telegram_chat_id = Column(String(50), nullable=True)
    bonus_ball = Column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)  # Bonus balance
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    driver_profile = relationship("Driver", back_populates="user", uselist=False)
    permission = relationship("Permission", back_populates="user", uselist=False)
    taxi_orders = relationship("TaxiOrder", back_populates="user", foreign_keys="TaxiOrder.user_id")
    delivery_orders = relationship("DeliveryOrder", back_populates="user", foreign_keys="DeliveryOrder.user_id")
    ratings_given = relationship("Rating", back_populates="user", foreign_keys="Rating.user_id")
    driver_application = relationship("DriverApplication", back_populates="user", foreign_keys="DriverApplication.user_id", uselist=False)
    device_tokens = relationship("DeviceToken", back_populates="user", foreign_keys="DeviceToken.user_id")


class Permission(Base):
    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    
    # Order permissions
    orders_view = Column(Boolean, default=False, nullable=False)
    orders_update = Column(Boolean, default=False, nullable=False)
    orders_cancel = Column(Boolean, default=False, nullable=False)
    create_order = Column(Boolean, default=False, nullable=False)
    
    # Driver permissions
    drivers_applications = Column(Boolean, default=False, nullable=False)
    drivers_list = Column(Boolean, default=False, nullable=False)
    drivers_block = Column(Boolean, default=False, nullable=False)
    drivers_delete = Column(Boolean, default=False, nullable=False)
    drivers_balance = Column(Boolean, default=False, nullable=False)
    
    # User permissions
    users_view = Column(Boolean, default=False, nullable=False)
    users_role = Column(Boolean, default=False, nullable=False)
    users_reset_password = Column(Boolean, default=False, nullable=False)
    users_bonus = Column(Boolean, default=False, nullable=False)
    
    # Pricing permissions
    pricing_view = Column(Boolean, default=False, nullable=False)
    pricing_edit = Column(Boolean, default=False, nullable=False)
    pricing_fee = Column(Boolean, default=False, nullable=False)
    
    # Stats and reports permissions
    stats_view = Column(Boolean, default=False, nullable=False)
    region_stats_view = Column(Boolean, default=False, nullable=False)
    admin_report_view = Column(Boolean, default=False, nullable=False)
    
    # Message and notification permissions
    messages_feedback = Column(Boolean, default=False, nullable=False)
    broadcast_send = Column(Boolean, default=False, nullable=False)
    
    # Profile permission
    profile = Column(Boolean, default=False, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="permission")


class Driver(Base):
    __tablename__ = "drivers"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    full_name = Column(String(100), nullable=False)
    car_model = Column(String(100), nullable=False)
    car_number = Column(String(20), nullable=False)
    license_photo = Column(String(255), nullable=False)
    car_photo = Column(String(255), nullable=True)
    tex_pas = Column(String(255), nullable=True)
    rating = Column(Numeric(3, 2), default=0.00)
    balance = Column(Numeric(10, 2), default=0.00)
    vip = Column(Boolean, default=False, nullable=False)
    vip_expires_at = Column(DateTime(timezone=True), nullable=True)
    brend = Column(Boolean, default=False, nullable=False)
    tariff = Column(
        SQLEnum(Tariff, name="tariff", values_callable=lambda obj: [e.value for e in obj]),
        default=Tariff.STANDARD,
        nullable=False,
    )
    is_blocked = Column(Boolean, default=False, nullable=False)
    is_worked = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="driver_profile")
    taxi_orders = relationship("TaxiOrder", back_populates="driver", foreign_keys="TaxiOrder.driver_id")
    delivery_orders = relationship("DeliveryOrder", back_populates="driver", foreign_keys="DeliveryOrder.driver_id")
    ratings_received = relationship("Rating", back_populates="driver", foreign_keys="Rating.driver_id")
    balance_transactions = relationship("BalanceTransaction", back_populates="driver")

    @property
    def telephone(self):
        return self.user.telephone if self.user else None


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


class DistrictPricing(Base):
    __tablename__ = "district_pricing"
    
    id = Column(Integer, primary_key=True, index=True)
    from_district_id = Column(Integer, ForeignKey("districts.id"), nullable=False)
    to_district_id = Column(Integer, ForeignKey("districts.id"), nullable=False)
    service_type = Column(String(20), nullable=False)  # "taxi" or "delivery"
    tariff = Column(
        SQLEnum(Tariff, name="tariff", values_callable=lambda obj: [e.value for e in obj]),
        default=Tariff.STANDARD,
        nullable=False,
    )
    base_price = Column(Numeric(10, 2), nullable=False)
    front_seat_price = Column(Numeric(10, 2), nullable=True)  # Price for front seat
    back_seat_price = Column(Numeric(10, 2), nullable=True)  # Price for back seat
    discount_1_passenger = Column(Numeric(5, 2), default=0.00)  # percentage
    discount_2_passengers = Column(Numeric(5, 2), default=0.00)
    discount_3_passengers = Column(Numeric(5, 2), default=0.00)
    discount_full_car = Column(Numeric(5, 2), default=0.00)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    from_district = relationship("District", foreign_keys=[from_district_id])
    to_district = relationship("District", foreign_keys=[to_district_id])


class TaxiOrder(Base):
    __tablename__ = "taxi_orders"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    driver_id = Column(Integer, ForeignKey("drivers.id"), nullable=True)
    bonus_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Optional user to receive bonus
    username = Column(String(100), nullable=False)
    telephone = Column(String(20), nullable=False)
    from_region_id = Column(Integer, ForeignKey("regions.id"), nullable=False)
    from_district_id = Column(Integer, ForeignKey("districts.id"), nullable=False)
    to_region_id = Column(Integer, ForeignKey("regions.id"), nullable=False)
    to_district_id = Column(Integer, ForeignKey("districts.id"), nullable=False)
    pickup_latitude = Column(String(50), nullable=True)  # Client's pickup latitude
    pickup_longitude = Column(String(50), nullable=True)  # Client's pickup longitude
    pickup_address = Column(Text, nullable=True)  # Optional address description
    dropoff_latitude = Column(String(50), nullable=True)  # Destination latitude
    dropoff_longitude = Column(String(50), nullable=True)  # Destination longitude
    dropoff_address = Column(Text, nullable=True)  # Destination address description
    passengers = Column(Integer, nullable=False)  # 1, 2, 3, 4
    client_gender = Column(SQLEnum(Gender, values_callable=lambda obj: [e.value for e in obj]), nullable=True)  # Client's gender for this order
    seat_type = Column(SQLEnum(SeatType, values_callable=lambda obj: [e.value for e in obj]), nullable=True)  # front or back
    tariff = Column(
        SQLEnum(Tariff, name="tariff", values_callable=lambda obj: [e.value for e in obj]),
        default=Tariff.STANDARD,
        nullable=False,
    )
    is_mail_delivery = Column(Boolean, default=False, nullable=False)  # True if sending package/item instead of passenger
    date = Column(String(10), nullable=False)  # dd.mm.yyyy
    time_start = Column(String(5), nullable=False)  # HH:MM
    time_end = Column(String(5), nullable=False)  # HH:MM
    scheduled_datetime = Column(DateTime(timezone=True), nullable=True)  # Scheduled pickup datetime
    price = Column(Numeric(10, 2), nullable=False)
    service_fee = Column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)  # 8% platform fee
    driver_earnings = Column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)  # Driver's portion after fee
    note = Column(Text, nullable=True)
    status = Column(SQLEnum(OrderStatus, values_callable=lambda obj: [e.value for e in obj]), default=OrderStatus.PENDING, nullable=False)
    public_order = Column(Boolean, default=False, nullable=False)  # If true, order is visible to all drivers
    is_new = Column(Boolean, default=True, nullable=False)
    pending_time = Column(Integer, nullable=True)  # Time in seconds before order becomes public
    cancellation_reason = Column(Text, nullable=True)
    cancelled_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    cancelled_by_role = Column(String(20), nullable=True)
    telegram_message_id = Column(Integer, nullable=True)
    accepted_at = Column(DateTime(timezone=True), nullable=True)
    confirmed_at = Column(DateTime(timezone=True), nullable=True)  # When driver confirms after accepting
    is_confirmed = Column(Boolean, default=False, nullable=False)  # Whether driver confirmed the order
    completed_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="taxi_orders", foreign_keys=[user_id])
    driver = relationship("Driver", back_populates="taxi_orders", foreign_keys=[driver_id])
    bonus_user = relationship("User", foreign_keys=[bonus_user_id])
    cancelled_by_user = relationship("User", foreign_keys=[cancelled_by_user_id])
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
    bonus_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Optional user to receive bonus
    username = Column(String(100), nullable=False)
    sender_telephone = Column(String(20), nullable=False)
    receiver_telephone = Column(String(20), nullable=False)
    from_region_id = Column(Integer, ForeignKey("regions.id"), nullable=False)
    from_district_id = Column(Integer, ForeignKey("districts.id"), nullable=False)
    to_region_id = Column(Integer, ForeignKey("regions.id"), nullable=False)
    to_district_id = Column(Integer, ForeignKey("districts.id"), nullable=False)
    pickup_latitude = Column(String(50), nullable=True)  # Sender's pickup latitude
    pickup_longitude = Column(String(50), nullable=True)  # Sender's pickup longitude
    pickup_address = Column(Text, nullable=True)  # Sender's address
    dropoff_latitude = Column(String(50), nullable=True)  # Receiver's drop-off latitude
    dropoff_longitude = Column(String(50), nullable=True)  # Receiver's drop-off longitude
    dropoff_address = Column(Text, nullable=True)  # Receiver's address
    who_pay = Column(String(20), nullable=False, default="recipient", server_default="recipient")  # sender or recipient
    item_type = Column(SQLEnum(ItemType, values_callable=lambda obj: [e.value for e in obj]), nullable=False)
    date = Column(String(10), nullable=False)  # dd.mm.yyyy
    time_start = Column(String(5), nullable=False)  # HH:MM
    time_end = Column(String(5), nullable=False)  # HH:MM
    scheduled_datetime = Column(DateTime(timezone=True), nullable=True)  # Scheduled pickup datetime
    price = Column(Numeric(10, 2), nullable=False)
    service_fee = Column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)  # 8% platform fee
    driver_earnings = Column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)  # Driver's portion after fee
    note = Column(Text, nullable=True)
    status = Column(SQLEnum(OrderStatus, values_callable=lambda obj: [e.value for e in obj]), default=OrderStatus.PENDING, nullable=False)
    public_order = Column(Boolean, default=False, nullable=False)  # If true, order is visible to all drivers
    is_new = Column(Boolean, default=True, nullable=False)
    pending_time = Column(Integer, nullable=True)  # Time in seconds before order becomes public
    cancellation_reason = Column(Text, nullable=True)
    cancelled_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    cancelled_by_role = Column(String(20), nullable=True)
    telegram_message_id = Column(Integer, nullable=True)
    accepted_at = Column(DateTime(timezone=True), nullable=True)
    confirmed_at = Column(DateTime(timezone=True), nullable=True)  # When driver confirms after accepting
    is_confirmed = Column(Boolean, default=False, nullable=False)  # Whether driver confirmed the order
    completed_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="delivery_orders", foreign_keys=[user_id])
    driver = relationship("Driver", back_populates="delivery_orders", foreign_keys=[driver_id])
    bonus_user = relationship("User", foreign_keys=[bonus_user_id])
    cancelled_by_user = relationship("User", foreign_keys=[cancelled_by_user_id])
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
    car_photo = Column(String(255), nullable=True)
    tex_pas = Column(String(255), nullable=True)
    status = Column(SQLEnum(ApplicationStatus, values_callable=lambda obj: [e.value for e in obj]), default=ApplicationStatus.PENDING, nullable=False)
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
    tariff = Column(
        SQLEnum(Tariff, name="tariff", values_callable=lambda obj: [e.value for e in obj]),
        default=Tariff.STANDARD,
        nullable=False,
    )
    base_price = Column(Numeric(10, 2), nullable=False)
    front_seat_price = Column(Numeric(10, 2), nullable=True)  # Price for front seat
    back_seat_price = Column(Numeric(10, 2), nullable=True)  # Price for back seat
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
    admin = relationship("User", foreign_keys=[admin_id], backref="balance_transactions_created")


class Notification(Base):
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    driver_id = Column(Integer, ForeignKey("drivers.id"), nullable=True)
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    body = Column(Text, nullable=False)
    data = Column(JSONB, nullable=True)
    notification_type = Column(String(50), nullable=False)
    is_read = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    driver = relationship("Driver", foreign_keys=[driver_id])


class DeviceToken(Base):
    __tablename__ = "device_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    token = Column(String(512), nullable=False, unique=True, index=True)
    platform = Column(
        SQLEnum(DevicePlatform, values_callable=lambda obj: [e.value for e in obj]),
        nullable=True,
    )
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_seen_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="device_tokens", foreign_keys=[user_id])


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


class OrderAcceptanceHistory(Base):
    """Track which drivers received but did not accept an order"""
    __tablename__ = "order_acceptance_history"
    
    id = Column(Integer, primary_key=True, index=True)
    driver_id = Column(Integer, ForeignKey("drivers.id"), nullable=False)
    taxi_order_id = Column(Integer, ForeignKey("taxi_orders.id"), nullable=True)
    delivery_order_id = Column(Integer, ForeignKey("delivery_orders.id"), nullable=True)
    received_at = Column(DateTime(timezone=True), server_default=func.now())
    action = Column(String(20), nullable=False)  # "received", "accepted", "returned_to_pending", "cancel_after_accept", "cancel_from_pending"
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    driver = relationship("Driver", foreign_keys=[driver_id])
    taxi_order = relationship("TaxiOrder", foreign_keys=[taxi_order_id])
    delivery_order = relationship("DeliveryOrder", foreign_keys=[delivery_order_id])


class Bonus(Base):
    """Bonus configuration model with percentage for bonus calculations"""
    __tablename__ = "bonuses"
    
    id = Column(Integer, primary_key=True, index=True)
    bonus_percent = Column(Numeric(5, 2), nullable=False, default=Decimal("5.00"))  # percentage
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class TopUpTransaction(Base):
    __tablename__ = "topup_transactions"
    __table_args__ = (
        UniqueConstraint("click_trans_id", name="uq_topup_click_trans_id"),
        UniqueConstraint("merchant_prepare_id", name="uq_topup_merchant_prepare_id"),
        UniqueConstraint("merchant_confirm_id", name="uq_topup_merchant_confirm_id"),
        Index("ix_topup_driver_created_at", "driver_id", "created_at"),
        Index("ix_topup_account_phone", "account_phone"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    merchant_trans_id = Column(String(64), nullable=False)
    account_phone = Column(String(20), nullable=True)
    driver_id = Column(Integer, ForeignKey("drivers.id"), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    status = Column(
        SQLEnum(
            TopUpStatus,
            name="topup_status",
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
    )
    click_trans_id = Column(String(64), nullable=True)
    merchant_prepare_id = Column(String(64), nullable=True)
    merchant_confirm_id = Column(String(64), nullable=True)
    error_code = Column(Integer, nullable=True)
    raw_prepare_payload = Column(JSONB, nullable=True)
    raw_complete_payload = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    paid_at = Column(DateTime(timezone=True), nullable=True)

    driver = relationship("Driver", foreign_keys=[driver_id])


class PaymentLog(Base):
    __tablename__ = "payment_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kind = Column(String(20), nullable=False)
    merchant_trans_id = Column(String(64), nullable=False)
    click_trans_id = Column(String(64), nullable=True)
    payload = Column(JSONB, nullable=False)
    response = Column(JSONB, nullable=True)
    request_id = Column(String(64), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
