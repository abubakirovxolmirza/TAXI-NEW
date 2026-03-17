from pydantic import BaseModel, validator, Field, root_validator
from typing import Optional, List, Literal
from datetime import datetime
from decimal import Decimal
from app.models import (
    UserRole,
    Language,
    Gender,
    OrderStatus,
    ApplicationStatus,
    ItemType,
    SeatType,
    Tariff,
    DevicePlatform,
    DriverPhotoControlStatus,
)


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
    telephone: Optional[str] = None
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


class SetPasswordRequest(BaseModel):
    """Schema for setting password without old password (for guest users)"""
    telephone: str = Field(..., description="User's telephone number")
    new_password: str = Field(..., min_length=6, description="New password (minimum 6 characters)")
    confirm_password: str = Field(..., description="Confirm new password")
    
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
    bonus_ball: Decimal
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class PermissionBase(BaseModel):
    # Order permissions
    orders_view: bool = False
    orders_update: bool = False
    orders_cancel: bool = False
    create_order: bool = False
    
    # Driver permissions
    drivers_applications: bool = False
    drivers_list: bool = False
    drivers_block: bool = False
    drivers_delete: bool = False
    drivers_balance: bool = False
    
    # User permissions
    users_view: bool = False
    users_role: bool = False
    users_reset_password: bool = False
    users_bonus: bool = False
    
    # Pricing permissions
    pricing_view: bool = False
    pricing_edit: bool = False
    pricing_fee: bool = False
    
    # Stats and reports permissions
    stats_view: bool = False
    region_stats_view: bool = False
    admin_report_view: bool = False
    
    # Message and notification permissions
    messages_feedback: bool = False
    broadcast_send: bool = False
    
    # Profile permission
    profile: bool = False


class PermissionCreate(PermissionBase):
    user_id: int


class PermissionUpdate(BaseModel):
    # Order permissions
    orders_view: Optional[bool] = None
    orders_update: Optional[bool] = None
    orders_cancel: Optional[bool] = None
    create_order: Optional[bool] = None
    
    # Driver permissions
    drivers_applications: Optional[bool] = None
    drivers_list: Optional[bool] = None
    drivers_block: Optional[bool] = None
    drivers_delete: Optional[bool] = None
    drivers_balance: Optional[bool] = None
    
    # User permissions
    users_view: Optional[bool] = None
    users_role: Optional[bool] = None
    users_reset_password: Optional[bool] = None
    users_bonus: Optional[bool] = None
    
    # Pricing permissions
    pricing_view: Optional[bool] = None
    pricing_edit: Optional[bool] = None
    pricing_fee: Optional[bool] = None
    
    # Stats and reports permissions
    stats_view: Optional[bool] = None
    region_stats_view: Optional[bool] = None
    admin_report_view: Optional[bool] = None
    
    # Message and notification permissions
    messages_feedback: Optional[bool] = None
    broadcast_send: Optional[bool] = None
    
    # Profile permission
    profile: Optional[bool] = None


class PermissionResponse(PermissionBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class DriverBonusInfo(BaseModel):
    id: int
    full_name: str
    car_model: str
    car_number: str
    tariff: Tariff

    class Config:
        from_attributes = True


class BonusBallUpdate(BaseModel):
    bonus_ball: Decimal = Field(..., ge=0)


class BonusBallUserResponse(BaseModel):
    id: int
    telephone: str
    name: str
    role: UserRole
    bonus_ball: Decimal
    driver_profile: Optional[DriverBonusInfo] = None

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
    bonus_user_id: Optional[int] = None  # Optional user to receive bonus
    from_region_id: int
    from_district_id: int
    to_region_id: int
    to_district_id: int
    pickup_latitude: Optional[str] = None  # Client's pickup latitude
    pickup_longitude: Optional[str] = None  # Client's pickup longitude
    pickup_address: Optional[str] = None  # Optional address description
    dropoff_latitude: Optional[str] = None  # Destination latitude
    dropoff_longitude: Optional[str] = None  # Destination longitude
    dropoff_address: Optional[str] = None  # Destination address description
    passengers: int = Field(..., ge=1, le=4)
    client_gender: Optional[Gender] = None  # Client's gender for this order (not required)
    seat_type: Optional[SeatType] = None  # front or back (auto-selected if not provided)
    tariff: Tariff = Tariff.STANDARD
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


class TaxiOrderUpdate(BaseModel):
    username: Optional[str] = None
    telephone: Optional[str] = None
    from_region_id: Optional[int] = None
    from_district_id: Optional[int] = None
    to_region_id: Optional[int] = None
    to_district_id: Optional[int] = None
    pickup_latitude: Optional[str] = None
    pickup_longitude: Optional[str] = None
    pickup_address: Optional[str] = None
    dropoff_latitude: Optional[str] = None
    dropoff_longitude: Optional[str] = None
    dropoff_address: Optional[str] = None
    passengers: Optional[int] = Field(None, ge=1, le=4)
    client_gender: Optional[Gender] = None
    seat_type: Optional[SeatType] = None
    tariff: Optional[Tariff] = None
    is_mail_delivery: Optional[bool] = None
    date: Optional[str] = None
    time_start: Optional[str] = None
    time_end: Optional[str] = None
    scheduled_datetime: Optional[datetime] = None
    price: Optional[Decimal] = None
    note: Optional[str] = None
    status: Optional[OrderStatus] = None


class TaxiOrderDriverInfo(BaseModel):
    id: int
    full_name: str
    telephone: Optional[str]
    profile_picture: Optional[str]
    car_model: str
    car_number: str
    rating: Decimal
    tariff: Tariff

    class Config:
        from_attributes = True


class TaxiOrderResponse(BaseModel):
    id: int
    user_id: int
    driver_id: Optional[int]
    bonus_user_id: Optional[int]
    username: str
    telephone: str
    from_region_id: int
    from_district_id: int
    to_region_id: int
    to_district_id: int
    pickup_latitude: Optional[str]
    pickup_longitude: Optional[str]
    pickup_address: Optional[str]
    dropoff_latitude: Optional[str]
    dropoff_longitude: Optional[str]
    dropoff_address: Optional[str]
    passengers: int
    client_gender: Optional[Gender]
    seat_type: Optional[SeatType]
    tariff: Tariff
    is_mail_delivery: bool
    date: str
    time_start: str
    time_end: str
    scheduled_datetime: Optional[datetime]  # Scheduled pickup datetime
    price: Decimal
    service_fee: Decimal
    driver_earnings: Decimal
    note: Optional[str]
    status: OrderStatus
    public_order: bool
    is_new: bool
    pending_time: Optional[int]
    cancellation_reason: Optional[str]
    cancelled_by_user_id: Optional[int]
    cancelled_by_user_name: Optional[str]
    cancelled_by_role: Optional[str]
    created_at: datetime
    accepted_at: Optional[datetime]
    confirmed_at: Optional[datetime]
    is_confirmed: bool
    completed_at: Optional[datetime]
    driver: Optional[TaxiOrderDriverInfo] = None
    
    class Config:
        from_attributes = True


# Delivery Order Schemas
class DeliveryOrderCreate(BaseModel):
    username: str
    sender_telephone: str
    receiver_telephone: str
    bonus_user_id: Optional[int] = None  # Optional user to receive bonus
    from_region_id: int
    from_district_id: int
    to_region_id: int
    to_district_id: int
    pickup_latitude: Optional[str] = None  # Sender's pickup latitude
    pickup_longitude: Optional[str] = None  # Sender's pickup longitude
    pickup_address: Optional[str] = None  # Sender's address
    dropoff_latitude: Optional[str] = None  # Receiver's drop-off latitude
    dropoff_longitude: Optional[str] = None  # Receiver's drop-off longitude
    dropoff_address: Optional[str] = None  # Receiver's address
    who_pay: Literal["sender", "recipient"] = "recipient"
    item_type: ItemType
    date: str  # dd.mm.yyyy
    time_start: str  # HH:MM
    time_end: str  # HH:MM
    scheduled_datetime: Optional[datetime] = None  # Scheduled pickup datetime (ISO format)
    note: Optional[str] = None


class DeliveryOrderUpdate(BaseModel):
    username: Optional[str] = None
    sender_telephone: Optional[str] = None
    receiver_telephone: Optional[str] = None
    from_region_id: Optional[int] = None
    from_district_id: Optional[int] = None
    to_region_id: Optional[int] = None
    to_district_id: Optional[int] = None
    pickup_latitude: Optional[str] = None
    pickup_longitude: Optional[str] = None
    pickup_address: Optional[str] = None
    dropoff_latitude: Optional[str] = None
    dropoff_longitude: Optional[str] = None
    dropoff_address: Optional[str] = None
    who_pay: Optional[Literal["sender", "recipient"]] = None
    item_type: Optional[ItemType] = None
    date: Optional[str] = None
    time_start: Optional[str] = None
    time_end: Optional[str] = None
    scheduled_datetime: Optional[datetime] = None
    price: Optional[Decimal] = None
    note: Optional[str] = None
    status: Optional[OrderStatus] = None


class DeliveryOrderResponse(BaseModel):
    id: int
    user_id: int
    driver_id: Optional[int]
    bonus_user_id: Optional[int]
    username: str
    sender_telephone: str
    receiver_telephone: str
    from_region_id: int
    from_district_id: int
    to_region_id: int
    to_district_id: int
    pickup_latitude: Optional[str]
    pickup_longitude: Optional[str]
    pickup_address: Optional[str]
    dropoff_latitude: Optional[str]
    dropoff_longitude: Optional[str]
    dropoff_address: Optional[str]
    who_pay: Literal["sender", "recipient"]
    item_type: ItemType
    date: str
    time_start: str
    time_end: str
    scheduled_datetime: Optional[datetime]  # Scheduled pickup datetime
    price: Decimal
    service_fee: Decimal
    driver_earnings: Decimal
    note: Optional[str]
    status: OrderStatus
    public_order: bool
    is_new: bool
    pending_time: Optional[int]
    cancellation_reason: Optional[str]
    cancelled_by_user_id: Optional[int]
    cancelled_by_user_name: Optional[str]
    cancelled_by_role: Optional[str]
    created_at: datetime
    accepted_at: Optional[datetime]
    confirmed_at: Optional[datetime]
    is_confirmed: bool
    completed_at: Optional[datetime]
    driver: Optional[TaxiOrderDriverInfo] = None
    
    class Config:
        from_attributes = True


# Driver Schemas
class DriverApplicationCreate(BaseModel):
    full_name: str
    car_model: str
    car_number: str
    license_photo: str  # file path after upload
    car_photo: Optional[str] = None  # file path after upload
    tex_pas: Optional[str] = None  # file path after upload


class DriverApplicationResponse(BaseModel):
    id: int
    user_id: int
    full_name: str
    telephone: str
    car_model: str
    car_number: str
    license_photo: str
    car_photo: Optional[str]
    tex_pas: Optional[str]
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
    car_photo: Optional[str] = None
    tex_pas: Optional[str] = None


class DriverWorkStatusUpdate(BaseModel):
    is_worked: bool


class DriverResponse(BaseModel):
    id: int
    user_id: int
    full_name: str
    telephone: Optional[str] = None
    profile_picture: Optional[str] = None
    bonus_ball: Decimal
    car_model: str
    car_number: str
    tariff: Tariff
    license_photo: str
    car_photo: Optional[str]
    tex_pas: Optional[str]
    rating: Decimal
    balance: Decimal
    vip: bool
    vip_expires_at: Optional[datetime]
    brend: bool
    is_blocked: bool
    is_worked: bool
    control: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class DriverVipUpdate(BaseModel):
    vip: bool
    vip_days: Optional[int] = Field(None, ge=1)

    @validator("vip_days", always=True)
    def validate_vip_days(cls, v, values):
        if values.get("vip") and v is None:
            raise ValueError("vip_days is required when vip is true")
        return v


class DriverBrendUpdate(BaseModel):
    brend: bool


class DriverTariffUpdate(BaseModel):
    tariff: Tariff


class DriverControlUpdate(BaseModel):
    control: bool


class DriverStatistics(BaseModel):
    daily_orders: int
    daily_revenue: Decimal
    monthly_orders: int
    monthly_revenue: Decimal
    total_orders: int
    total_revenue: Decimal
    current_balance: Decimal
    rating: Decimal


class ActiveDriverStatsItem(BaseModel):
    driver_id: int
    full_name: str
    telephone: Optional[str] = None
    car_number: str
    tariff: Tariff
    rating: Decimal
    balance: Decimal
    accepted_orders: int
    completed_orders: int
    cancelled_orders: int
    total_orders: int
    revenue: Decimal
    completion_rate: Decimal
    cancellation_rate: Decimal
    avg_revenue_per_completed: Decimal


class ActiveDriverStatsResponse(BaseModel):
    period: Literal["daily", "monthly", "yearly"]
    start_date: datetime
    end_date: datetime
    drivers: List[ActiveDriverStatsItem]


class DriverPhotoControlSubmitRequest(BaseModel):
    front_image: str = Field(..., min_length=1, max_length=255)
    back_image: str = Field(..., min_length=1, max_length=255)
    front_salon: str = Field(..., min_length=1, max_length=255)
    back_salon: str = Field(..., min_length=1, max_length=255)
    trunk_image: str = Field(..., min_length=1, max_length=255)


class DriverPhotoControlReviewRequest(BaseModel):
    approved: bool
    rejection_reason: Optional[str] = Field(default=None, max_length=500)

    @validator("rejection_reason", always=True)
    def validate_rejection_reason(cls, v, values):
        if values.get("approved") is False and not (v and v.strip()):
            raise ValueError("rejection_reason is required when approved is false")
        return v


class DriverPhotoControlToggleRequest(BaseModel):
    control: bool


class DriverPhotoControlIntervalUpdate(BaseModel):
    days: int = Field(..., ge=1, le=365)


class DriverPhotoControlResponse(BaseModel):
    id: int
    driver_id: int
    front_image: str
    back_image: str
    front_salon: str
    back_salon: str
    trunk_image: str
    status: DriverPhotoControlStatus
    rejection_reason: Optional[str] = None
    created_at: datetime
    approved_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DriverPhotoControlCheckResponse(BaseModel):
    required: bool
    can_submit_now: bool
    window_start_hour: int
    window_end_hour: int
    interval_days: int
    status: str
    latest: Optional[DriverPhotoControlResponse] = None
    next_due_at: Optional[datetime] = None


class DriverPhotoControlUploadResponse(BaseModel):
    message: str
    file_path: str


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
    tariff: Tariff = Tariff.STANDARD
    base_price: Decimal
    front_seat_price: Optional[Decimal] = None
    back_seat_price: Optional[Decimal] = None
    discount_1_passenger: Decimal = Decimal("0.00")
    discount_2_passengers: Decimal = Decimal("0.00")
    discount_3_passengers: Decimal = Decimal("0.00")
    discount_full_car: Decimal = Decimal("0.00")

    @validator("tariff")
    def validate_tariff_for_service_type(cls, v, values):
        if values.get("service_type") == "delivery" and v != Tariff.STANDARD:
            raise ValueError("Delivery pricing supports only standard tariff")
        return v


class PricingUpdate(BaseModel):
    tariff: Optional[Tariff] = None
    base_price: Optional[Decimal] = None
    front_seat_price: Optional[Decimal] = None
    back_seat_price: Optional[Decimal] = None
    discount_1_passenger: Optional[Decimal] = None
    discount_2_passengers: Optional[Decimal] = None
    discount_3_passengers: Optional[Decimal] = None
    discount_full_car: Optional[Decimal] = None


class PricingResponse(BaseModel):
    id: int
    from_region_id: int
    to_region_id: int
    service_type: str
    tariff: Tariff
    base_price: Decimal
    front_seat_price: Optional[Decimal]
    back_seat_price: Optional[Decimal]
    discount_1_passenger: Decimal
    discount_2_passengers: Decimal
    discount_3_passengers: Decimal
    discount_full_car: Decimal
    is_active: bool
    
    class Config:
        from_attributes = True


class PricingBulkAdjustRequest(BaseModel):
    operation: Literal["add", "subtract"]
    amount: Decimal = Field(..., gt=0)


class PricingBulkAdjustResponse(BaseModel):
    success: bool
    service_type: str
    operation: str
    amount: Decimal
    updated_region_pricing_count: int
    updated_district_pricing_count: int


# Balance Transaction Schemas
class BalanceAdd(BaseModel):
    driver_id: int
    amount: Decimal
    description: Optional[str] = None


class BonusToBalanceConvertRequest(BaseModel):
    amount: Decimal = Field(..., gt=0)


class BonusToBalanceConvertResponse(BaseModel):
    success: bool
    message: str
    transferred_amount: Decimal
    bonus_ball: Decimal
    balance: Decimal
    transaction_id: int


class DriverBalanceHistoryItem(BaseModel):
    id: int
    amount: Decimal
    transaction_type: str
    description: Optional[str]
    source: str
    source_label: str
    admin_id: Optional[int]
    admin_name: Optional[str]
    created_at: datetime


class DriverBalanceHistoryResponse(BaseModel):
    total: int
    current_balance: Decimal
    vip: bool
    transactions: List[DriverBalanceHistoryItem]


class BalanceTransactionResponse(BaseModel):
    id: int
    driver_id: int
    amount: Decimal
    transaction_type: str
    description: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class BalanceHistoryDetail(BaseModel):
    id: int
    driver_id: int
    driver_name: str
    amount: Decimal
    transaction_type: str
    description: Optional[str]
    admin_id: Optional[int]
    admin_name: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


# District Pricing Schemas
class DistrictPricingCreate(BaseModel):
    from_district_id: Optional[int] = None
    to_district_id: Optional[int] = None
    from_district_ids: Optional[List[int]] = None
    to_district_ids: Optional[List[int]] = None
    service_type: str  # "taxi" or "delivery"
    tariff: Tariff = Tariff.STANDARD
    base_price: Decimal
    front_seat_price: Optional[Decimal] = None
    back_seat_price: Optional[Decimal] = None
    discount_1_passenger: Decimal = Decimal("0.00")
    discount_2_passengers: Decimal = Decimal("0.00")
    discount_3_passengers: Decimal = Decimal("0.00")
    discount_full_car: Decimal = Decimal("0.00")

    @validator("tariff")
    def validate_tariff_for_service_type(cls, v, values):
        if values.get("service_type") == "delivery" and v != Tariff.STANDARD:
            raise ValueError("Delivery pricing supports only standard tariff")
        return v

    @root_validator(skip_on_failure=True)
    def validate_district_inputs(cls, values):
        from_single = values.get("from_district_id")
        to_single = values.get("to_district_id")
        from_many = values.get("from_district_ids") or []
        to_many = values.get("to_district_ids") or []

        if from_single is None and not from_many:
            raise ValueError("At least one from district is required")
        if to_single is None and not to_many:
            raise ValueError("At least one to district is required")

        return values


class DistrictPricingUpdate(BaseModel):
    tariff: Optional[Tariff] = None
    base_price: Optional[Decimal] = None
    front_seat_price: Optional[Decimal] = None
    back_seat_price: Optional[Decimal] = None
    discount_1_passenger: Optional[Decimal] = None
    discount_2_passengers: Optional[Decimal] = None
    discount_3_passengers: Optional[Decimal] = None
    discount_full_car: Optional[Decimal] = None


class DistrictPricingResponse(BaseModel):
    id: int
    from_district_id: int
    to_district_id: int
    service_type: str
    tariff: Tariff
    base_price: Decimal
    front_seat_price: Optional[Decimal]
    back_seat_price: Optional[Decimal]
    discount_1_passenger: Decimal
    discount_2_passengers: Decimal
    discount_3_passengers: Decimal
    discount_full_car: Decimal
    is_active: bool
    
    class Config:
        from_attributes = True


# Region and District Creation with Pricing
class RegionCreateWithPricing(BaseModel):
    name_uz_latin: str
    name_uz_cyrillic: str
    name_russian: str


class DistrictCreateWithPricing(BaseModel):
    name_uz_latin: str
    name_uz_cyrillic: str
    name_russian: str
    region_id: int


# Notification Schemas
class NotificationResponse(BaseModel):
    id: int
    title: str
    message: str
    body: Optional[str] = None
    data: Optional[dict] = None
    notification_type: str
    is_read: bool
    created_at: datetime

    @validator("body", pre=True, always=True)
    def set_body_from_message(cls, v, values):
        if v is not None:
            return v
        return values.get("message")

    @validator("created_at", pre=True, always=True)
    def convert_created_at_to_uzbek_time(cls, v):
        from app.utils import get_uzbek_time
        if v is None:
            return v
        return get_uzbek_time(v)
    
    class Config:
        from_attributes = True


# Broadcast Message Schema
class BroadcastMessage(BaseModel):
    target: str  # "users", "drivers", "all"
    title: str
    message: str


class DeviceTokenUpsertRequest(BaseModel):
    token: str = Field(..., min_length=20, max_length=2048)
    platform: Optional[DevicePlatform] = None


class DeviceTokenDeleteRequest(BaseModel):
    token: str = Field(..., min_length=20, max_length=2048)


class DeviceTokenResponse(BaseModel):
    id: int
    user_id: int
    token: str
    platform: Optional[DevicePlatform]
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]
    last_seen_at: Optional[datetime]

    class Config:
        from_attributes = True


class DeviceTokenActionResponse(BaseModel):
    success: bool
    message: str
    device_token: Optional[DeviceTokenResponse] = None


class DeviceRegisterRequest(BaseModel):
    user_id: Optional[int] = None
    driver_id: Optional[int] = None
    token: str = Field(..., min_length=20, max_length=2048)
    platform: Optional[DevicePlatform] = DevicePlatform.ANDROID


class NotificationSendRequest(BaseModel):
    user_id: int
    title: str = Field(..., min_length=1, max_length=200)
    body: str = Field(..., min_length=1)
    data: Optional[dict] = None


class NotificationBroadcastRequest(BaseModel):
    user_ids: List[int] = Field(..., min_items=1)
    title: str = Field(..., min_length=1, max_length=200)
    body: str = Field(..., min_length=1)
    data: Optional[dict] = None


class PushSendSummary(BaseModel):
    total_tokens: int
    success_count: int
    failure_count: int
    invalidated_tokens: int
    skipped: bool = False
    failure_reasons: List[dict] = Field(default_factory=list)


class NotificationSendResponse(BaseModel):
    success: bool
    notification: NotificationResponse
    push: PushSendSummary


class NotificationBroadcastResponse(BaseModel):
    success: bool
    notifications_created: int
    push: PushSendSummary


class NotificationCreateRequest(BaseModel):
    user_id: Optional[int] = None
    driver_id: Optional[int] = None
    title: str = Field(..., min_length=1, max_length=200)
    body: str = Field(..., min_length=1)
    type: str = Field(default="message", min_length=1, max_length=100)
    data: Optional[dict] = None


# Order Cancellation Schema
class OrderCancellation(BaseModel):
    order_id: int
    order_type: str  # "taxi" or "delivery"
    cancellation_reason: str


# Bulk Delete Schema
class BulkDeleteRequest(BaseModel):
    order_ids: List[int] = Field(..., min_items=1, description="List of order IDs to delete")


# Feedback Schema
class FeedbackCreate(BaseModel):
    message: str


class FeedbackReplyRequest(BaseModel):
    message: str = Field(..., min_length=1, description="Reply text sent to the user")


class FeedbackUserInfo(BaseModel):
    name: str
    telephone: str

    class Config:
        from_attributes = True


class FeedbackResponse(BaseModel):
    id: int
    user_id: Optional[int]
    user: Optional[FeedbackUserInfo] = None
    telegram_chat_id: Optional[str]
    message: str
    is_reviewed: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


# System Settings Schemas
class ServiceFeeUpdate(BaseModel):
    service_fee_percentage: Decimal = Field(..., ge=0, le=100)
    
    @validator('service_fee_percentage')
    def validate_percentage(cls, v):
        if v < 0 or v > 100:
            raise ValueError('Service fee percentage must be between 0 and 100')
        return v


class ServiceFeeResponse(BaseModel):
    service_fee_percentage: Decimal
    updated_at: Optional[datetime]
    updated_by: Optional[int]


class SystemSettingResponse(BaseModel):
    setting_key: str
    setting_value: str
    description: Optional[str]
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


# Bonus Schemas
class BonusCreate(BaseModel):
    bonus_percent: Decimal = Field(..., ge=0, le=100, description="Bonus percentage (0-100)")
    description: Optional[str] = None
    is_active: bool = True
    
    @validator('bonus_percent')
    def validate_percentage(cls, v):
        if v < 0 or v > 100:
            raise ValueError('Bonus percentage must be between 0 and 100')
        return v


class BonusUpdate(BaseModel):
    bonus_percent: Optional[Decimal] = Field(None, ge=0, le=100)
    description: Optional[str] = None
    is_active: Optional[bool] = None


class BonusResponse(BaseModel):
    id: int
    bonus_percent: Decimal
    description: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


# Order Acceptance History Schemas
class OrderAcceptanceHistoryResponse(BaseModel):
    id: int
    driver_id: int
    taxi_order_id: Optional[int]
    delivery_order_id: Optional[int]
    received_at: datetime
    action: str
    created_at: datetime
    
    class Config:
        from_attributes = True


# Pending Time Update Schema
class PendingTimeUpdate(BaseModel):
    pending_time: int = Field(..., ge=1, description="Pending time in minutes")


# Public Order Response (extended from regular order response)
class PublicTaxiOrderResponse(TaxiOrderResponse):
    public_order: bool
    pending_time: Optional[int]


class PublicDeliveryOrderResponse(DeliveryOrderResponse):
    public_order: bool
    pending_time: Optional[int]
