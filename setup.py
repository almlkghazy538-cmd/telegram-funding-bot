hereimport os
import sys

def setup():
    print("🚀 إعداد مشروع بوت تمويل القنوات")
    print("=" * 50)
    
    # 1. تثبيت المتطلبات
    print("\n1️⃣ تثبيت المكتبات المطلوبة...")
    os.system("pip install -r requirements.txt")
    
    # 2. نسخ ملف .env
    print("\n2️⃣ إنشاء ملف الإعدادات...")
    if not os.path.exists(".env"):
        with open(".env", "w") as f:
            f.write("BOT_TOKEN=8436742877:AAFLSbZzdssjGodD1CmyOMNdTvAIlcUtmuw\n")
            f.write("ADMIN_ID=6130994941\n")
            f.write("DATABASE_URL=sqlite:///bot_database.db\n")
        print("✅ تم إنشاء ملف .env")
    else:
        print("✅ ملف .env موجود بالفعل")
    
    # 3. إنشاء قاعدة البيانات
    print("\n3️⃣ إنشاء قاعدة البيانات...")
    from database import Base, engine
    Base.metadata.create_all(engine)
    print("✅ تم إنشاء قاعدة البيانات")
    
    # 4. تعيين المدير الرئيسي
    print("\n4️⃣ تعيين المدير الرئيسي...")
    from database import session, User
    from config import Config
    
    admin = session.query(User).filter_by(user_id=Config.ADMIN_ID).first()
    if not admin:
        admin = User(
            user_id=Config.ADMIN_ID,
            username="admin",
            first_name="مدير النظام",
            is_admin=True,
            admin_permissions='["all"]'
        )
        session.add(admin)
        session.commit()
        print(f"✅ تم تعيين المستخدم {Config.ADMIN_ID} كمشرف رئيسي")
    else:
        print("✅ المدير موجود بالفعل")
    
    print("\n" + "=" * 50)
    print("✅ تم الإعداد بنجاح!")
    print("\n🔧 الخطوات التالية:")
    print("1. افتح ملف .env وضع توكن البوت")
    print("2. شغل البوت: python main.py")
    print("3. ابدأ بإضافة القنوات والمجموعات من لوحة التحكم")

if __name__ == "__main__":
    setup()
