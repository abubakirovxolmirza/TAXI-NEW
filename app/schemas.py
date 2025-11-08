from pydantic import BaseModel, validator, Field
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from app.models import UserRole, Language, OrderStatus, ApplicationStatus, ItemType


# User Schemas
class UserBase(BaseModel):
    telephone: str
    name: str


class UserCreate(UserBase):
    password: str
    confirm_password: str
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'password' in values and v != values['password']:
            raise ValueError('Passwords do not match')
        return v


class UserLogin(BaseModel):
    telephone: str
    password: str


class UserUpdate(BaseModel):
    name: Optional[str] = None
    language: Optional[Language] = None
    profile_picture: Optional[str] = None


class PasswordChange(BaseModel):
    old_password: str
    new_password: str
    confirm_password: str
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v


class UserRoleUpdate(BaseModel):
    user_id: int
    role: UserRole


class UserResponse(UserBase):
    id: int
    role: UserRole
    language: Language
    profile_picture: Optional[str]
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse


# Region/District Schemas
class DistrictBase(BaseModel):
    name_uz_latin: str
    name_uz_cyrillic: str
    name_russian: str


class DistrictCreate(DistrictBase):
    region_id: int


class DistrictResponse(DistrictBase):
    id: int
    region_id: int
    is_active: bool
    
    class Config:
        from_attributes = True


class RegionBase(BaseModel):
    name_uz_latin: str
    name_uz_cyrillic: str
    name_russian: str


class RegionCreate(RegionBase):
    pass


class RegionResponse(RegionBase):
    id: int
    is_active: bool
    districts: List[DistrictResponse] = []
    
    class Config:
        from_attributes = True


# Taxi Order Schemas
class TaxiOrderCreate(BaseModel):
    username: str
    telephone: str
    from_region_id: int
    from_district_id: int
    to_region_id: int
    to_district_id: int
    pickup_latitude: Optional[float] = None  # Client's pickup latitude
    pickup_longitude: Optional[float] = None  # Client's pickup longitude
    pickup_address: Optional[str] = None  # Optional address description
    passengers: int = Field(..., ge=1, le=4)
    is_mail_delivery: bool = False  # True if sending package/item instead of passenger
    date: str  # dd.mm.yyyy
    time_start: str  # HH:MM
    time_end: str  # HH:MM
    scheduled_datetime: Optional[datetime] = None  # Scheduled pickup datetime (ISO format)
    note: Optional[str] = None
    
    @validator('to_region_id')
    def regions_must_differ(cls, v, values):
        if 'from_region_id' in values and v == values['from_region_id']:
            raise ValueError('To region cannot be the same as from region')
        return v


class TaxiOrderResponse(BaseModel):
    id: int
    user_id: int
    driver_id: Optional[int]
    username: str
    telephone: str
    from_region_id: int
    from_district_id: int
    to_region_id: int
    to_district_id: int
    pickup_latitude: Optional[Decimal]
    pickup_longitude: Optional[Decimal]
    pickup_address: Optional[str]
    passengers: int
    is_mail_delivery: bool
    date: str
    time_start: str
    time_end: str
    scheduled_datetime: Optional[datetime]  # Scheduled pickup datetime
    price: Decimal
    note: Optional[str]
    status: OrderStatus
    cancellation_reason: Optional[str]
    created_at: datetime
    accepted_at: Optional[datetime]
    completed_at: Optional[datetime]
    
    class Config:
        from_attributes = True


# Delivery Order Schemas
class DeliveryOrderCreate(BaseModel):
    username: str
    sender_telephone: str
    receiver_telephone: str
    from_region_id: int
    from_district_id: int
    to_region_id: int
    to_district_id: int
    pickup_latitude: Optional[float] = None  # Sender's pickup latitude
    pickup_longitude: Optional[float] = None  # Sender's pickup longitude
    pickup_address: Optional[str] = None  # Sender's address
    dropoff_latitude: Optional[float] = None  # Receiver's drop-off latitude
    dropoff_longitude: Optional[float] = None  # Receiver's drop-off longitude
    dropoff_address: Optional[str] = None  # Receiver's address
    item_type: ItemType
    date: str  # dd.mm.yyyy
    time_start: str  # HH:MM
    time_end: str  # HH:MM
    scheduled_datetime: Optional[datetime] = None  # Scheduled pickup datetime (ISO format)
    note: Optional[str] = None


class DeliveryOrderResponse(BaseModel):
    id: int
    user_id: int
    driver_id: Optional[int]
    username: str
    sender_telephone: str
    receiver_telephone: str
    from_region_id: int
    from_district_id: int
    to_region_id: int
    to_district_id: int
    pickup_latitude: Optional[Decimal]
    pickup_longitude: Optional[Decimal]
    pickup_address: Optional[str]
    dropoff_latitude: Optional[Decimal]
    dropoff_longitude: Optional[Decimal]
    dropoff_address: Optional[str]
    item_type: ItemType
    date: str
    time_start: str
    time_end: str
    scheduled_datetime: Optional[datetime]  # Scheduled pickup datetime
    price: Decimal
    note: Optional[str]
    status: OrderStatus
    cancellation_reason: Optional[str]
    created_at: datetime
    accepted_at: Optional[datetime]
    completed_at: Optional[datetime]
    
    class Config:
        from_attributes = True


# Driver Schemas
class DriverApplicationCreate(BaseModel):
    full_name: str
    car_model: str
    car_number: str
    license_photo: str  # file path after upload


class DriverApplicationResponse(BaseModel):
    id: int
    user_id: int
    full_name: str
    telephone: str
    car_model: str
    car_number: str
    license_photo: str
    status: ApplicationStatus
    rejection_reason: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class DriverApplicationReview(BaseModel):
    application_id: int
    approved: bool
    rejection_reason: Optional[str] = None


class DriverUpdate(BaseModel):
    full_name: Optional[str] = None
    car_model: Optional[str] = None
    car_number: Optional[str] = None


class DriverResponse(BaseModel):
    id: int
    user_id: int
    full_name: str
    car_model: str
    car_number: str
    rating: Decimal
    balance: Decimal
    is_blocked: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class DriverStatistics(BaseModel):
    daily_orders: int
    daily_revenue: Decimal
    monthly_orders: int
    monthly_revenue: Decimal
    total_orders: int
    total_revenue: Decimal
    current_balance: Decimal
    rating: Decimal


# Rating Schemas
class RatingCreate(BaseModel):
    driver_id: int
    order_id: int
    order_type: str  # "taxi" or "delivery"
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None


class RatingResponse(BaseModel):
    id: int
    user_id: int
    driver_id: int
    rating: int
    comment: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


# Pricing Schemas
class PricingCreate(BaseModel):
    from_region_id: int
    to_region_id: int
    service_type: str  # "taxi" or "delivery"
    base_price: Decimal
    discount_1_passenger: Decimal = Decimal("0.00")
    discount_2_passengers: Decimal = Decimal("0.00")
    discount_3_passengers: Decimal = Decimal("0.00")
    discount_full_car: Decimal = Decimal("0.00")


class PricingUpdate(BaseModel):
    base_price: Optional[Decimal] = None
    discount_1_passenger: Optional[Decimal] = None
    discount_2_passengers: Optional[Decimal] = None
    discount_3_passengers: Optional[Decimal] = None
    discount_full_car: Optional[Decimal] = None


class PricingResponse(BaseModel):
    id: int
    from_region_id: int
    to_region_id: int
    service_type: str
    base_price: Decimal
    discount_1_passenger: Decimal
    discount_2_passengers: Decimal
    discount_3_passengers: Decimal
    discount_full_car: Decimal
    is_active: bool
    
    class Config:
        from_attributes = True


# Balance Transaction Schemas
class BalanceAdd(BaseModel):
    driver_id: int
    amount: Decimal
    description: Optional[str] = None


class BalanceTransactionResponse(BaseModel):
    id: int
    driver_id: int
    amount: Decimal
    transaction_type: str
    description: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


# Notification Schemas
class NotificationResponse(BaseModel):
    id: int
    title: str
    message: str
    notification_type: str
    is_read: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


# Broadcast Message Schema
class BroadcastMessage(BaseModel):
    target: str  # "users", "drivers", "all"
    title: str
    message: str


# Order Cancellation Schema
class OrderCancellation(BaseModel):
    order_id: int
    order_type: str  # "taxi" or "delivery"
    cancellation_reason: str


# Feedback Schema
class FeedbackCreate(BaseModel):
    message: str


class FeedbackResponse(BaseModel):
    id: int
    user_id: Optional[int]
    telegram_chat_id: Optional[str]
    message: str
    is_reviewed: bool
    created_at: datetime
    
    class Config:
        from_attributes = True
