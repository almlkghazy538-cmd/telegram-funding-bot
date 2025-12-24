import asyncio
import logging
from telegram import Bot
from telegram.error import TelegramError, UserPrivacyRestrictedError
from database import get_db, GroupSource, FundingRequest, User
from config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MemberAdder:
    def __init__(self, bot: Bot):
        self.bot = bot
    
    async def add_members_to_channel(self, request_id: int):
        """إضافة أعضاء للقناة من المجموعات المصدر"""
        db = get_db()
        try:
            request = db.query(FundingRequest).filter_by(id=request_id).first()
            if not request or request.status != 'approved':
                return
            
            user = db.query(User).filter_by(user_id=request.user_id).first()
            if not user:
                return
            
            target_channel = request.target_channel
            needed_members = request.requested_members
            added_count = 0
            
            logger.info(f"بدء إضافة {needed_members} عضو للقناة {target_channel}")
            
            # إعلام المستخدم بالبدء
            try:
                await self.bot.send_message(
                    user.user_id,
                    f"🚀 بدأت عملية إضافة الأعضاء لطلبك #{request_id}\n"
                    f"👥 العدد المطلوب: {needed_members} عضو"
                )
            except:
                pass
            
            # الحصول على المجموعات المصدر النشطة
            source_groups = db.query(GroupSource).filter_by(is_active=True).all()
            
            for group in source_groups:
                if added_count >= needed_members:
                    break
                
                try:
                    # جلب أعضاء المجموعة
                    members_added = await self.add_members_from_group(
                        group.group_id,
                        target_channel,
                        needed_members - added_count
                    )
                    
                    added_count += members_added
                    logger.info(f"تمت إضافة {members_added} عضو من مجموعة {group.group_title}")
                    
                    # تحديث حالة الطلب
                    request.completed_members = added_count
                    db.commit()
                    
                    # تأخير بين المجموعات
                    await asyncio.sleep(5)
                    
                except Exception as e:
                    logger.error(f"خطأ في المجموعة {group.group_id}: {e}")
                    continue
            
            # تحديث الحالة النهائية
            if added_count > 0:
                request.status = 'completed'
                success_message = f"✅ تم الانتهاء من طلبك #{request.id}\n👥 تمت إضافة {added_count} عضو بنجاح!"
            else:
                request.status = 'failed'
                success_message = f"❌ فشل طلبك #{request.id}\n⚠️ لم تتم إضافة أي عضو."
            
            db.commit()
            
            # إعلام المستخدم
            try:
                await self.bot.send_message(user.user_id, success_message)
            except:
                pass
            
            return added_count
            
        except Exception as e:
            logger.error(f"خطأ في إضافة الأعضاء: {e}")
            return 0
        finally:
            db.close()
    
    async def add_members_from_group(self, source_group_id: str, target_channel: str, max_members: int):
        """إضافة أعضاء من مجموعة مصدر معينة"""
        added_count = 0
        
        try:
            # جلب قائمة الأعضاء (بحدود معينة)
            members = await self.get_group_members(source_group_id, max_members * 2)
            
            logger.info(f"جاري معالجة {len(members)} عضو من المجموعة {source_group_id}")
            
            for member in members:
                if added_count >= max_members:
                    break
                
                try:
                    # محاولة إضافة العضو للقناة
                    await self.bot.add_chat_members(
                        chat_id=target_channel,
                        user_ids=[member.user.id]
                    )
                    
                    added_count += 1
                    logger.info(f"تمت إضافة العضو {member.user.id} بنجاح")
                    
                    # تأخير بين كل إضافة لتجنب الحظر
                    await asyncio.sleep(Config.ADD_MEMBERS_DELAY)
                    
                except UserPrivacyRestrictedError:
                    logger.debug(f"العضو {member.user.id} مقيد الخصوصية")
                    continue
                    
                except TelegramError as e:
                    if "USER_ALREADY_PARTICIPANT" in str(e):
                        logger.debug(f"العضو {member.user.id} موجود بالفعل")
                        added_count += 1
                    elif "USER_NOT_MUTUAL_CONTACT" in str(e):
                        logger.debug(f"العضو {member.user.id} ليس جهة اتصال متبادلة")
                    elif "CHAT_ADMIN_REQUIRED" in str(e):
                        logger.error(f"البوت ليس أدمن في القناة الهدف")
                        break
                    else:
                        logger.warning(f"خطأ في إضافة العضو {member.user.id}: {e}")
                    continue
                except Exception as e:
                    logger.error(f"خطأ غير متوقع: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"خطأ في جلب أعضاء المجموعة {source_group_id}: {e}")
        
        return added_count
    
    async def get_group_members(self, group_id: str, limit: int = 100):
        """جلب قائمة أعضاء المجموعة"""
        members = []
        
        try:
            # ملاحظة: هذه الدالة قد تحتاج لتعديل حسب صلاحيات البوت
            async for member in self.bot.get_chat_members(group_id):
                if len(members) >= limit:
                    break
                
                # استبعاد البوتات والمشرفين
                if not member.user.is_bot and member.status == 'member':
                    members.append(member)
        
        except Exception as e:
            logger.error(f"خطأ في جلب أعضاء المجموعة: {e}")
        
        return members

async def process_pending_requests(bot: Bot):
    """معالجة طلبات التمويل المعلقة"""
    adder = MemberAdder(bot)
    logger.info("بدء معالج طلبات التمويل...")
    
    while True:
        try:
            db = get_db()
            
            # البحث عن طلبات معتمدة تحتاج معالجة
            pending_requests = db.query(FundingRequest).filter_by(status='approved').all()
            
            logger.info(f"وجدت {len(pending_requests)} طلب معتمد للمعالجة")
            
            for request in pending_requests:
                logger.info(f"معالجة الطلب #{request.id}")
                await adder.add_members_to_channel(request.id)
            
            db.close()
            
            # انتظار 5 دقائق بين كل جولة
            await asyncio.sleep(300)
            
        except Exception as e:
            logger.error(f"خطأ في معالجة الطلبات: {e}")
            await asyncio.sleep(60)
