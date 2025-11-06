import logging
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, filters, ContextTypes
)
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import User, Region, District, TaxiOrder, DeliveryOrder, Language, UserRole
from app.config import settings
from decimal import Decimal

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Conversation states
(
    MAIN_MENU, LANGUAGE_SELECTION, TAXI_BOOKING, DELIVERY_ORDER,
    DRIVER_APPLICATION, FEEDBACK, CONTACT_INFO
) = range(7)

# Sub-states for taxi booking
(
    TAXI_USERNAME, TAXI_PHONE, TAXI_FROM_REGION, TAXI_FROM_DISTRICT,
    TAXI_TO_REGION, TAXI_TO_DISTRICT, TAXI_PASSENGERS, TAXI_DATE,
    TAXI_TIME_START, TAXI_TIME_END, TAXI_NOTE
) = range(11, 22)

# Sub-states for delivery
(
    DELIVERY_USERNAME, DELIVERY_SENDER_PHONE, DELIVERY_RECEIVER_PHONE,
    DELIVERY_FROM_REGION, DELIVERY_FROM_DISTRICT, DELIVERY_TO_REGION,
    DELIVERY_TO_DISTRICT, DELIVERY_ITEM_TYPE, DELIVERY_DATE,
    DELIVERY_TIME_START, DELIVERY_TIME_END, DELIVERY_NOTE
) = range(22, 34)


def get_db():
    db = SessionLocal()
    try:
        return db
    finally:
        db.close()


def get_main_keyboard(language: str = "uz_latin"):
    """Get main menu keyboard based on language"""
    keyboards = {
        "uz_latin": [
            ["🚖 Taksi buyurtma qilish", "📦 Yetkazib berish"],
            ["🚗 Haydovchi bo'lish", "💬 Fikr bildirish"],
            ["📞 Aloqa", "🌐 Tilni o'zgartirish"]
        ],
        "uz_cyrillic": [
            ["🚖 Такси буюртма қилиш", "📦 Етказиб бериш"],
            ["🚗 Ҳайдовчи бўлиш", "💬 Фикр билдириш"],
            ["📞 Алоқа", "🌐 Тилни ўзгартириш"]
        ],
        "russian": [
            ["🚖 Заказать такси", "📦 Доставка"],
            ["🚗 Стать водителем", "💬 Оставить отзыв"],
            ["📞 Контакты", "🌐 Изменить язык"]
        ]
    }
    return ReplyKeyboardMarkup(keyboards.get(language, keyboards["uz_latin"]), resize_keyboard=True)


def get_language_keyboard():
    """Get language selection keyboard"""
    keyboard = [
        ["🇺🇿 O'zbek (lotin)", "🇺🇿 Ўзбек (кирилл)", "🇷🇺 Русский"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command handler"""
    user = update.effective_user
    chat_id = str(update.effective_chat.id)
    
    db = SessionLocal()
    
    # Check if user exists
    db_user = db.query(User).filter(User.telegram_chat_id == chat_id).first()
    
    if not db_user:
        # New user - ask for language
        await update.message.reply_text(
            "🌐 Tilni tanlang / Выберите язык:",
            reply_markup=get_language_keyboard()
        )
        db.close()
        return LANGUAGE_SELECTION
    else:
        # Existing user
        language = db_user.language.value
        welcome_messages = {
            "uz_latin": f"Assalomu alaykum, {db_user.name}! Xizmatni tanlang:",
            "uz_cyrillic": f"Ассалому алайкум, {db_user.name}! Хизматни танланг:",
            "russian": f"Здравствуйте, {db_user.name}! Выберите услугу:"
        }
        
        await update.message.reply_text(
            welcome_messages.get(language, welcome_messages["uz_latin"]),
            reply_markup=get_main_keyboard(language)
        )
        db.close()
        return MAIN_MENU


async def handle_language_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle language selection"""
    choice = update.message.text
    
    language_map = {
        "🇺🇿 O'zbek (lotin)": "uz_latin",
        "🇺🇿 Ўзбек (кирилл)": "uz_cyrillic",
        "🇷🇺 Русский": "russian"
    }
    
    selected_language = language_map.get(choice, "uz_latin")
    context.user_data['language'] = selected_language
    
    # Ask for phone number
    phone_request_messages = {
        "uz_latin": "📱 Telefon raqamingizni yuboring (masalan: +998901234567):",
        "uz_cyrillic": "📱 Телефон рақамингизни юборинг (масалан: +998901234567):",
        "russian": "📱 Отправьте ваш номер телефона (например: +998901234567):"
    }
    
    await update.message.reply_text(phone_request_messages[selected_language])
    return MAIN_MENU


async def handle_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle main menu selection"""
    choice = update.message.text
    
    # Map choices to handlers
    if "Taksi" in choice or "Такси" in choice or "такси" in choice:
        # Start taxi booking
        await update.message.reply_text("Ismingizni kiriting:")
        return TAXI_USERNAME
    elif "Yetkazib" in choice or "Етказиб" in choice or "Доставка" in choice:
        # Start delivery order
        await update.message.reply_text("Ismingizni kiriting:")
        return DELIVERY_USERNAME
    elif "Haydovchi" in choice or "Ҳайдовчи" in choice or "водителем" in choice:
        # Driver application
        await update.message.reply_text("To'liq ismingizni kiriting:")
        return DRIVER_APPLICATION
    elif "Fikr" in choice or "Фикр" in choice or "отзыв" in choice:
        # Feedback
        await update.message.reply_text("Fikr yoki taklifingizni yozing:")
        return FEEDBACK
    elif "Aloqa" in choice or "Алоқа" in choice or "Контакты" in choice:
        # Contact info
        contact_text = """
📞 Aloqa ma'lumotlari:
Telefon: +998 90 123 45 67
Email: support@taxiservice.uz
Manzil: Toshkent, Uzbekistan
        """
        await update.message.reply_text(contact_text)
        return MAIN_MENU
    elif "Til" in choice or "язык" in choice:
        # Change language
        await update.message.reply_text(
            "Tilni tanlang / Выберите язык:",
            reply_markup=get_language_keyboard()
        )
        return LANGUAGE_SELECTION
    
    return MAIN_MENU


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel conversation"""
    await update.message.reply_text("Bekor qilindi. /start buyrug'ini bosing.")
    return ConversationHandler.END


def main():
    """Run the bot"""
    # Create application
    application = Application.builder().token(settings.USER_BOT_TOKEN).build()
    
    # Add conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            LANGUAGE_SELECTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_language_selection)],
            MAIN_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_main_menu)],
            # Add more states here for taxi booking, delivery, etc.
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    
    application.add_handler(conv_handler)
    
    # Run the bot
    logger.info("Starting Telegram bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
