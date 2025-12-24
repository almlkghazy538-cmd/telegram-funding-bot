from sqlalchemy import create_engine, Column, Integer, String, Boolean, BigInteger, DateTime, Text, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import json

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String(100))
    first_name = Column(String(100))
    last_name = Column(String(100))
    points = Column(Integer, default=0)
    referrals = Column(Integer, default=0)
    referred_by = Column(BigInteger, nullable=True)
    is_banned = Column(Boolean, default=False)
    ban_reason = Column(Text, nullable=True)
    is_admin = Column(Boolean, default=False)
    admin_permissions = Column(String(500), default='[]')
    last_daily_gift = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.now)

class Channel(Base):
    __tablename__ = 'channels'
    id = Column(Integer, primary_key=True)
    channel_id = Column(String(100), nullable=False)
    channel_username = Column(String(100))
    channel_title = Column(String(200))
    is_private = Column(Boolean, default=False)
    is_mandatory = Column(Boolean, default=False)
    required_members = Column(Integer, default=0)
    current_members = Column(Integer, default=0)
    added_by_admin = Column(BigInteger)
    created_at = Column(DateTime, default=datetime.now)

class GroupSource(Base):
    __tablename__ = 'group_sources'
    id = Column(Integer, primary_key=True)
    group_id = Column(String(100), nullable=False)
    group_username = Column(String(100))
    group_title = Column(String(200))
    is_private = Column(Boolean, default=False)
    member_count = Column(Integer, default=0)
    added_by_admin = Column(BigInteger)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)

class FundingRequest(Base):
    __tablename__ = 'funding_requests'
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, nullable=False)
    target_channel = Column(String(100), nullable=False)
    target_type = Column(String(20), nullable=False)
    requested_members = Column(Integer, nullable=False)
    points_cost = Column(Integer, nullable=False)
    status = Column(String(20), default='pending')
    approved_by = Column(BigInteger, nullable=True)
    completed_members = Column(Integer, default=0)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

class PointsTransfer(Base):
    __tablename__ = 'points_transfers'
    id = Column(Integer, primary_key=True)
    from_user_id = Column(BigInteger, nullable=False)
    to_user_id = Column(BigInteger, nullable=False)
    amount = Column(Integer, nullable=False)
    fee_percent = Column(Integer, nullable=False)
    fee_amount = Column(Integer, nullable=False)
    net_amount = Column(Integer, nullable=False)
    transfer_date = Column(DateTime, default=datetime.now)

class SystemSettings(Base):
    __tablename__ = 'system_settings'
    id = Column(Integer, primary_key=True)
    maintenance_mode = Column(Boolean, default=False)
    maintenance_message = Column(Text, default='البوت تحت الصيانة حالياً')
    transfer_enabled = Column(Boolean, default=True)
    transfer_fee_percent = Column(Integer, default=5)
    updated_by = Column(BigInteger, nullable=True)
    updated_at = Column(DateTime, default=datetime.now)

class PointsSettings(Base):
    __tablename__ = 'points_settings'
    id = Column(Integer, primary_key=True)
    points_per_member = Column(Integer, default=25)
    points_per_referral = Column(Integer, default=5)
    daily_gift_points = Column(Integer, default=3)
    points_per_channel = Column(Integer, default=2)
    min_points_for_funding = Column(Integer, default=25)
    updated_by = Column(BigInteger, nullable=True)
    updated_at = Column(DateTime, default=datetime.now)

class AdminContact(Base):
    __tablename__ = 'admin_contacts'
    id = Column(Integer, primary_key=True)
    admin_user_id = Column(BigInteger, nullable=False)
    admin_username = Column(String(100))
    is_active = Column(Boolean, default=True)
    added_by = Column(BigInteger)
    added_at = Column(DateTime, default=datetime.now)

# إنشاء المحرك والجلسة
engine = create_engine('sqlite:///bot_database.db', echo=False)
SessionLocal = sessionmaker(bind=engine)

def get_db():
    """الحصول على جلسة قاعدة البيانات"""
    db = SessionLocal()
    try:
        return db
    finally:
        db.close()

def init_database():
    """تهيئة قاعدة البيانات"""
    Base.metadata.create_all(engine)
    db = get_db()
    
    try:
        # إعدادات النظام
        if db.query(SystemSettings).count() == 0:
            system_settings = SystemSettings()
            db.add(system_settings)
        
        # إعدادات النقاط
        if db.query(PointsSettings).count() == 0:
            points_settings = PointsSettings()
            db.add(points_settings)
        
        # المدير الرئيسي
        admin_user = db.query(User).filter_by(user_id=6130994941).first()
        if not admin_user:
            admin_user = User(
                user_id=6130994941,
                username="admin",
                first_name="مدير النظام",
                is_admin=True,
                admin_permissions='["all"]'
            )
            db.add(admin_user)
        
        db.commit()
        print("✅ تم تهيئة قاعدة البيانات بنجاح")
    except Exception as e:
        print(f"❌ خطأ في تهيئة قاعدة البيانات: {e}")
        db.rollback()
    finally:
        db.close()
