import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # إعدادات أساسية
    BOT_TOKEN = os.getenv("BOT_TOKEN", "8436742877:AAGhCfnC9hbW7Sa4gMTroYissoljCjda9Ow")
    ADMIN_ID = int(os.getenv("ADMIN_ID", 6130994941))
    
    # إعدادات قاعدة البيانات
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///bot_database.db")
    
    # إعدادات النظام
    MAINTENANCE_MODE = False
    MAINTENANCE_MESSAGE = "البوت تحت الصيانة حالياً"
    TRANSFER_FEE_PERCENT = 5
    TRANSFER_ENABLED = True
    
    # إعدادات النقاط
    POINTS_PER_REFERRAL = 5
    DAILY_GIFT_POINTS = 3
    POINTS_PER_CHANNEL_SUB = 2
    MIN_POINTS_FOR_FUNDING = 25
    POINTS_PER_MEMBER = 25
    
    # إعدادات الأداء
    MAX_MEMBERS_PER_REQUEST = 50
    ADD_MEMBERS_DELAY = 1
    PORT = 8080
