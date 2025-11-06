import logging
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes
)
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import SessionLocal
from app.models import (
    User, DriverApplication, ApplicationStatus, Driver,
    TaxiOrder, DeliveryOrder, UserRole, Notification
)
from app.config import settings

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def admin_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin bot start command"""
    chat_id = str(update.effective_chat.id)
    
    # Check if user is admin
    db = SessionLocal()
    user = db.query(User).filter(
        User.telegram_chat_id == chat_id,
        User.role.in_([UserRole.ADMIN, UserRole.SUPERADMIN])
    ).first()
    db.close()
    
    if not user:
        await update.message.reply_text("⚠️ You are not authorized to use this bot.")
        return
    
    keyboard = [
        [InlineKeyboardButton("📋 Pending Applications", callback_data="pending_apps")],
        [InlineKeyboardButton("📊 View Statistics", callback_data="statistics")],
        [InlineKeyboardButton("👥 Manage Drivers", callback_data="manage_drivers")],
        [InlineKeyboardButton("📢 Broadcast Message", callback_data="broadcast")],
        [InlineKeyboardButton("💰 Add Driver Balance", callback_data="add_balance")],
        [InlineKeyboardButton("💬 View Feedback", callback_data="feedback")]
    ]
    
    if user.role == UserRole.SUPERADMIN:
        keyboard.append([InlineKeyboardButton("👨‍💼 Manage Admins", callback_data="manage_admins")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "👨‍💼 *Admin Panel*\n\nWelcome to the admin panel. Choose an option:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle callback queries from inline keyboards"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    db = SessionLocal()
    
    if data == "pending_apps":
        # Show pending driver applications
        applications = db.query(DriverApplication).filter(
            DriverApplication.status == ApplicationStatus.PENDING
        ).all()
        
        if not applications:
            await query.edit_message_text("No pending applications.")
            db.close()
            return
        
        text = "*Pending Driver Applications:*\n\n"
        keyboard = []
        
        for app in applications:
            text += f"ID: {app.id}\n"
            text += f"Name: {app.full_name}\n"
            text += f"Phone: {app.telephone}\n"
            text += f"Car: {app.car_model} ({app.car_number})\n\n"
            
            keyboard.append([
                InlineKeyboardButton(f"✅ Approve #{app.id}", callback_data=f"approve_{app.id}"),
                InlineKeyboardButton(f"❌ Reject #{app.id}", callback_data=f"reject_{app.id}")
            ])
        
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="back_to_menu")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    
    elif data == "statistics":
        # Show statistics
        total_users = db.query(func.count(User.id)).scalar()
        total_drivers = db.query(func.count(Driver.id)).scalar()
        pending_taxi = db.query(func.count(TaxiOrder.id)).filter(
            TaxiOrder.status == "pending"
        ).scalar()
        pending_delivery = db.query(func.count(DeliveryOrder.id)).filter(
            DeliveryOrder.status == "pending"
        ).scalar()
        
        text = f"""
📊 *Statistics*

👥 Total Users: {total_users}
🚗 Total Drivers: {total_drivers}
🚖 Pending Taxi Orders: {pending_taxi}
📦 Pending Delivery Orders: {pending_delivery}
        """
        
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back_to_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    
    elif data.startswith("approve_"):
        # Approve driver application
        app_id = int(data.split("_")[1])
        application = db.query(DriverApplication).filter(
            DriverApplication.id == app_id
        ).first()
        
        if application and application.status == ApplicationStatus.PENDING:
            # Create driver profile
            from app.models import Driver
            new_driver = Driver(
                user_id=application.user_id,
                full_name=application.full_name,
                car_model=application.car_model,
                car_number=application.car_number,
                license_photo=application.license_photo
            )
            db.add(new_driver)
            
            # Update application status
            application.status = ApplicationStatus.APPROVED
            
            # Update user role
            user = db.query(User).filter(User.id == application.user_id).first()
            if user:
                user.role = UserRole.DRIVER
            
            db.commit()
            
            await query.edit_message_text(
                f"✅ Application #{app_id} approved successfully!"
            )
        else:
            await query.edit_message_text("Application not found or already processed.")
    
    elif data.startswith("reject_"):
        # Reject driver application
        app_id = int(data.split("_")[1])
        await query.edit_message_text(
            f"Please send the rejection reason for application #{app_id}:"
        )
        context.user_data['rejecting_app'] = app_id
    
    elif data == "back_to_menu":
        # Go back to main menu
        keyboard = [
            [InlineKeyboardButton("📋 Pending Applications", callback_data="pending_apps")],
            [InlineKeyboardButton("📊 View Statistics", callback_data="statistics")],
            [InlineKeyboardButton("👥 Manage Drivers", callback_data="manage_drivers")],
            [InlineKeyboardButton("📢 Broadcast Message", callback_data="broadcast")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "👨‍💼 *Admin Panel*\n\nChoose an option:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    
    db.close()


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages (for rejection reasons, broadcast messages, etc.)"""
    if 'rejecting_app' in context.user_data:
        app_id = context.user_data['rejecting_app']
        reason = update.message.text
        
        db = SessionLocal()
        application = db.query(DriverApplication).filter(
            DriverApplication.id == app_id
        ).first()
        
        if application:
            application.status = ApplicationStatus.REJECTED
            application.rejection_reason = reason
            db.commit()
            
            await update.message.reply_text(
                f"✅ Application #{app_id} rejected with reason: {reason}"
            )
        
        db.close()
        del context.user_data['rejecting_app']


def main():
    """Run the admin bot"""
    application = Application.builder().token(settings.ADMIN_BOT_TOKEN).build()
    
    application.add_handler(CommandHandler('start', admin_start))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
    
    logger.info("Starting Admin Telegram bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
