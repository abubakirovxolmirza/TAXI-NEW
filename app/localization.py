# Uzbek Notification Messages
# This file contains all notification messages translated to Uzbek

NOTIFICATIONS = {
    # Order notifications
    "taxi_order_created": {
        "title": "Taksi buyurtmasi yaratildi",
        "message": "#{order_id} raqamli taksi buyurtmangiz yaratildi va haydovchilarni kutmoqda."
    },
    "delivery_order_created": {
        "title": "Yetkazib berish buyurtmasi yaratildi", 
        "message": "#{order_id} raqamli yetkazib berish buyurtmangiz yaratildi va haydovchilarni kutmoqda."
    },
    "order_accepted": {
        "title": "Buyurtma qabul qilindi",
        "message": "#{order_id} raqamli {order_type} buyurtmangiz haydovchi tomonidan qabul qilindi."
    },
    "order_completed": {
        "title": "Buyurtma yakunlandi",
        "message": "#{order_id} raqamli {order_type} buyurtmangiz yakunlandi. Iltimos, haydovchiga baho bering."
    },
    "order_confirmed": {
        "title": "Buyurtma tasdiqlandi",
        "message": "#{order_id} raqamli {order_type} buyurtmangiz haydovchi tomonidan tasdiqlandi."
    },
    "order_cancelled": {
        "title": "Buyurtma bekor qilindi",
        "message": "#{order_id} raqamli taksi buyurtmangiz bekor qilindi. Sabab: {reason}"
    },
    "order_cancelled_user": {
        "title": "Buyurtma bekor qilindi", 
        "message": "#{order_id} raqamli taksi buyurtmangiz muvaffaqiyatli bekor qilindi."
    },
    "order_returned": {
        "title": "Buyurtma qaytarildi",
        "message": "#{order_id} raqamli {order_type} buyurtmangiz haydovchi tomonidan rad etildi va boshqa haydovchilar uchun mavjud."
    },
    "order_expired": {
        "title": "Buyurtma muddati tugadi",
        "message": "#{order_id} raqamli {order_type} buyurtmasi tasdiqlash vaqti tugadi (15 daqiqa). Buyurtma umumiy ro'yxatga qaytarildi."
    },
    "order_expired_user": {
        "title": "Buyurtma muddati tugadi",
        "message": "#{order_id} raqamli {order_type} buyurtmangiz boshqa haydovchilar uchun mavjud."
    },
    
    # Financial notifications
    "service_fee_refunded": {
        "title": "Xizmat haqi qaytarildi",
        "message": "#{order_id} raqamli buyurtma uchun xizmat haqi qaytarildi."
    },
    "service_fee_deducted": {
        "title": "Xizmat haqi yechildi", 
        "message": "#{order_id} raqamli buyurtma uchun {amount} so'm xizmat haqi hisobingizdan yechildi."
    },
    "bonus_earned": {
        "title": "Bonus qo'shildi",
        "message": "#{order_id} raqamli buyurtmadan {amount} so'm bonus oldingiz."
    },
    
    # Rating notifications
    "new_rating": {
        "title": "Yangi baho",
        "message": "Sizga mijoz tomonidan {rating} yulduzli baho berildi."
    },
    
    # WebSocket notifications
    "websocket_connected": {
        "message": "WebSocket muvaffaqiyatli ulandi"
    },
    "lock_failed": {
        "message": "Buyurtmani olish muvaffaqiyatsiz, boshqa kishi qabul qilmoqda"
    },
    
    # System notifications
    "orders_deleted_all": {
        "message": "Barcha yetkazib berish buyurtmalari muvaffaqiyatli o'chirildi"
    },
    "order_deleted": {
        "message": "Buyurtma muvaffaqiyatli o'chirildi"
    },
    "orders_deleted_batch": {
        "message": "{count} ta buyurtma muvaffaqiyatli o'chirildi"
    },
    "order_deletion_failed": {
        "reason": "Faqat bekor qilingan yoki yakunlangan buyurtmalarni o'chirish mumkin"
    }
}

# Helper function to get localized message
def get_notification_message(key: str, **kwargs) -> dict:
    """
    Get localized notification message with parameters
    
    Args:
        key: Message key from NOTIFICATIONS dict
        **kwargs: Parameters to format into the message
    
    Returns:
        dict with title and message, or just message
    """
    if key not in NOTIFICATIONS:
        return {"message": f"Message not found: {key}"}
    
    notification = NOTIFICATIONS[key].copy()
    
    # Format message with provided parameters
    if "message" in notification and kwargs:
        notification["message"] = notification["message"].format(**kwargs)
    
    if "title" in notification and kwargs:
        notification["title"] = notification["title"].format(**kwargs)
    
    return notification