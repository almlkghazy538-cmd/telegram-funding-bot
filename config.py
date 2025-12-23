import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN", "8436742877:AAFLSbZzdssjGodD1CmyOMNdTvAIlcUtmuw")
    ADMIN_ID = int(os.getenv("ADMIN_ID", 6130994941))
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///bot_database.db")
    
    # إعدادات النقاط
    POINTS_PER_REFERRAL = 5
    DAILY_GIFT_POINTS = 3
    POINTS_PER_CHANNEL_SUB = 2
    MIN_POINTS_FOR_FUNDING = 25
    POINTS_PER_MEMBER = 25  # عدد النقاط لكل عضو
    
    # إعدادات السحب
    MAX_MEMBERS_PER_REQUEST = 50
    ADD_MEMBERS_DELAY = 1  # ثانية بين كل إضافة
