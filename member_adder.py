hereimport asyncio
from telegram import Bot
from telegram.error import TelegramError, UserPrivacyRestrictedError
from database import session, GroupSource, FundingRequest, User
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MemberAdder:
    def __init__(self, bot: Bot):
        self.bot = bot
    
    async def add_members_to_channel(self, request_id: int):
        """إضافة أعضاء للقناة من المجموعات المصدر"""
        request = session.query(FundingRequest).filter_by(id=request_id).first()
        if not request or request.status != 'approved':
            return
        
        user = session.query(User).filter_by(user_id=request.user_id).first()
        if not user:
            return
        
        target_channel = request.target_channel
        needed_members = request.requested_members
        added_count = 0
        
        # الحصول على المجموعات المصدر النشطة
        source_groups = session.query(GroupSource).filter_by(is_active=True).all()
        
        logger.info(f"بدء إضافة {needed_members} عضو للقناة {target_channel}")
        
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
                
                # تأخير بين المجموعات
                await asyncio.sleep(5)
                
            except Exception as e:
                logger.error(f"خطأ في المجموعة {group.group_id}: {e}")
                continue
        
        # تحديث حالة الطلب
        request.completed_members = added_count
        request.status = 'completed' if added_count > 0 else 'failed'
        session.commit()
        
        # إعلام المستخدم
        if added_count > 0:
            try:
                await self.bot.send_message(
                    user.user_id,
                    f"✅ تم الانتهاء من طلبك #{request.id}\n"
                    f"👥 تمت إضافة {added_count} عضو بنجاح!\n"
                    f"💰 تم خصم {request.points_cost} نقطة"
                )
            except:
                pass
        
        return added_count
    
    async def add_members_from_group(self, source_group_id: str, target_channel: str, max_members: int):
        """إضافة أعضاء من مجموعة مصدر معينة"""
        added_count = 0
        
        try:
            # جلب قائمة الأعضاء (بحدود معينة)
            members = await self.get_group_members(source_group_id, max_members * 2)
            
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
                    await asyncio.sleep(1)
                    
                except UserPrivacyRestrictedError:
                    logger.info(f"العضو {member.user.id} مقيد الخصوصية")
                    continue
                    
                except TelegramError as e:
                    if "USER_ALREADY_PARTICIPANT" in str(e):
                        logger.info(f"العضو {member.user.id} موجود بالفعل")
                        added_count += 1
                    elif "USER_NOT_MUTUAL_CONTACT" in str(e):
                        logger.info(f"العضو {member.user.id} ليس جهة اتصال متبادلة")
                    else:
                        logger.warning(f"خطأ في إضافة العضو {member.user.id}: {e}")
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
    
    while True:
        try:
            # البحث عن طلبات معتمدة تحتاج معالجة
            pending_requests = session.query(FundingRequest).filter_by(status='approved').all()
            
            for request in pending_requests:
                logger.info(f"معالجة الطلب #{request.id}")
                await adder.add_members_to_channel(request.id)
            
            # انتظار 5 دقائق بين كل جولة
            await asyncio.sleep(300)
            
        except Exception as e:
            logger.error(f"خطأ في معالجة الطلبات: {e}")
            await asyncio.sleep(60)
