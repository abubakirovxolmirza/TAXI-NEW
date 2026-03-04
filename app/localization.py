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
    "delivery_order_created_recipient": {
        "title": "Sizga yetkazma yuborildi",
        "message": "#{order_id} raqamli yetkazib berish buyurtmasida siz qabul qiluvchi sifatida ko'rsatildingiz."
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
        "message": "#{order_id} raqamli {order_type} buyurtmangiz muvaffaqiyatli bekor qilindi."
    },
    "order_cancelled_by_driver": {
        "title": "Buyurtma bekor qilindi",
        "message": "#{order_id} raqamli {order_type} buyurtmasi bekor qilindi. Sabab: {reason}"
    },
    "order_cancelled_by_admin": {
        "title": "Buyurtma bekor qilindi",
        "message": "#{order_id} raqamli {order_type} buyurtmangiz admin tomonidan bekor qilindi. Sabab: {reason}"
    },
    "order_cancelled_by_admin_driver": {
        "title": "Buyurtma bekor qilindi",
        "message": "#{order_id} raqamli {order_type} buyurtmasi admin tomonidan bekor qilindi."
    },
    "order_updated_by_admin": {
        "title": "Buyurtma yangilandi",
        "message": "#{order_id} raqamli {order_type} buyurtmangiz admin tomonidan yangilandi."
    },
    "order_updated_by_admin_driver": {
        "title": "Buyurtma yangilandi",
        "message": "#{order_id} raqamli {order_type} buyurtmasi admin tomonidan yangilandi."
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
    "order_status_update": {
        "title": "Buyurtma holati yangilandi",
        "message": "#{order_id} raqamli {order_type} buyurtmangiz endi boshqa haydovchilar uchun mavjud."
    },
    "order_released": {
        "title": "Buyurtma bo'shatildi",
        "message": "#{order_id} raqamli {order_type} buyurtmasini ko'rib chiqish muddati tugadi. Buyurtma umumiy ro'yxatga qaytarildi."
    },
    "order_now_public": {
        "title": "Buyurtma endi umumiy",
        "message": "#{order_id} raqamli {order_type} buyurtmangiz endi barcha haydovchilar uchun ko'rinadi."
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
    
    # Account management notifications
    "account_blocked": {
        "title": "Hisob bloklandi",
        "message": "Haydovchi hisobingiz admin tomonidan bloklandi."
    },
    "account_unblocked": {
        "title": "Hisob blokdan chiqarildi",
        "message": "Haydovchi hisobingiz blokdan chiqarildi."
    },
    "driver_profile_deleted": {
        "title": "Haydovchi profili o'chirildi",
        "message": "Haydovchi profilingiz admin tomonidan o'chirildi. Foydalanuvchi hisobingiz faol."
    },
    "balance_added": {
        "title": "Balans to'ldirildi",
        "message": "Hisobingizga {amount} so'm qo'shildi."
    },
    "admin_access_granted": {
        "title": "Admin huquqi berildi",
        "message": "Sizga admin huquqi berildi."
    },
    "role_updated": {
        "title": "Rol yangilandi",
        "message": "{message}"
    },
    "account_deactivated": {
        "title": "Hisob faolsizlantirildi",
        "message": "Hisobingiz admin tomonidan faolsizlantirildi."
    },
    "account_activated": {
        "title": "Hisob faollashtirildi",
        "message": "Hisobingiz faollashtirildi."
    },
    "password_reset": {
        "title": "Parol tiklandi",
        "message": "Parolingiz admin tomonidan tiklandi."
    },
    "application_approved": {
        "title": "Ariza tasdiqlandi",
        "message": "Tabriklaymiz! Haydovchilik arizangiz tasdiqlandi."
    },
    "application_rejected": {
        "title": "Ariza rad etildi",
        "message": "Haydovchilik arizangiz rad etildi. Sabab: {reason}"
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
