import asyncio
import logging
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from config import Config
from database import init_database
from bot_handlers import start_command, handle_message, button_handler
from admin_handlers import handle_admin_callback, handle_admin_input, approve_funding_request, reject_funding_request
from member_adder import process_pending_requests
from keep_alive import keep_alive

# إعداد التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def main():
    """الدالة الرئيسية لتشغيل البوت"""
    # التحقق من التوكن
    if Config.BOT_TOKEN == "ضع_توكن_البوت_هنا":
        print("❌ خطأ: لم تقم بوضع توكن البوت!")
        print("🔧 قم بتعديل ملف config.py أو .env ووضع التوكن الصحيح")
        return
    
    # تهيئة قاعدة البيانات
    print("🔄 جاري تهيئة قاعدة البيانات...")
    init_database()
    
    # بدء خدمات البقاء نشط (للسيرفرات المجانية)
    keep_alive()
    print("✅ تم تشغيل خدمات البقاء نشط")
    
    # إنشاء تطبيق البوت
    print("🤖 جاري إنشاء تطبيق البوت...")
    application = Application.builder().token(Config.BOT_TOKEN).build()
    
    # إضافة المعالجات
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(CallbackQueryHandler(handle_admin_callback))
    
    # معالجات الطلبات
    application.add_handler(CallbackQueryHandler(approve_funding_request, pattern="^approve_request_"))
    application.add_handler(CallbackQueryHandler(reject_funding_request, pattern="^reject_request_"))
    
    # معالجة الرسائل النصية
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # معالجة مدخلات الإدارة
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_input))
    
    # بدء معالجة الطلبات في الخلفية
    async def start_background_tasks():
        """بدء المهام في الخلفية"""
        logger.info("بدء مهام الخلفية...")
        asyncio.create_task(process_pending_requests(application.bot))
    
    # بدء البوت
    print("🚀 جاري تشغيل البوت...")
    print(f"👑 المدير الرئيسي: {Config.ADMIN_ID}")
    
    # بدء المهام الخلفية
    await start_background_tasks()
    
    # بدء الاستماع للتحديثات
    await application.run_polling(allowed_updates="all")

if __name__ == '__main__':
    # تشغيل البوت
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 تم إيقاف البوت")
    except Exception as e:
        print(f"❌ خطأ غير متوقع: {e}")
