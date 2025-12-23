import asyncio
import logging
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ConversationHandler
from config import Config
from database import session, User
from bot_handlers import start_command, handle_message, button_handler, handle_admin_buttons
from admin_panel_handlers import handle_admin_callback
from member_adder import process_pending_requests

# إعداد التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# تعريف حالات المحادثة
(
    AWAITING_MEMBER_COUNT,
    AWAITING_CHANNEL_LINK
) = range(2)

def main():
    """تشغيل البوت"""
    # إنشاء التطبيق
    application = Application.builder().token(Config.BOT_TOKEN).build()
    
    # إضافة المعالجات
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(CallbackQueryHandler(handle_admin_callback))
    application.add_handler(CallbackQueryHandler(handle_admin_buttons))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # تعيين المستخدم الرئيسي كمشرف
    admin_user = session.query(User).filter_by(user_id=Config.ADMIN_ID).first()
    if not admin_user:
        admin_user = User(
            user_id=Config.ADMIN_ID,
            username="admin",
            first_name="مدير النظام",
            is_admin=True,
            admin_permissions='["all"]'
        )
        session.add(admin_user)
        session.commit()
        logger.info(f"تم تعيين المستخدم {Config.ADMIN_ID} كمشرف رئيسي")
    elif not admin_user.is_admin:
        admin_user.is_admin = True
        admin_user.admin_permissions = '["all"]'
        session.commit()
        logger.info(f"تم ترقية المستخدم {Config.ADMIN_ID} إلى مشرف")
    
    # بدء معالجة الطلبات في الخلفية
    async def start_background_tasks():
        """بدء المهام في الخلفية"""
        asyncio.create_task(process_pending_requests(application.bot))
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)
    
    # بدء المهام عند التشغيل
    loop = asyncio.get_event_loop()
    loop.create_task(start_background_tasks())

if __name__ == '__main__':
    main()
