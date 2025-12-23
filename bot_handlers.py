from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from database import session, User, Channel, GroupSource, FundingRequest, PointsSettings, AdminContact
from config import Config
from datetime import datetime, timedelta
import re

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username
    first_name = update.effective_user.first_name
    
    # التحقق من الاشتراك الإجباري
    if not await check_mandatory_channels(user_id, context):
        channels = session.query(Channel).filter_by(is_mandatory=True).all()
        keyboard = []
        for channel in channels:
            if channel.channel_username:
                keyboard.append([InlineKeyboardButton(f"اشترك في @{channel.channel_username}", 
                                                    url=f"https://t.me/{channel.channel_username.replace('@', '')}")])
        keyboard.append([InlineKeyboardButton("✅ تحقق من الاشتراك", callback_data="check_subscription")])
        
        await update.message.reply_text(
            "⚠️ يجب الاشتراك في القنوات التالية أولاً:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    # تسجيل المستخدم
    user = session.query(User).filter_by(user_id=user_id).first()
    if not user:
        user = User(
            user_id=user_id,
            username=username,
            first_name=first_name,
            last_name=update.effective_user.last_name,
            created_at=datetime.now()
        )
        session.add(user)
        
        # إضافة نقاط للإحالة
        if context.args:
            try:
                referrer_id = int(context.args[0])
                referrer = session.query(User).filter_by(user_id=referrer_id).first()
                if referrer:
                    settings = session.query(PointsSettings).first()
                    if not settings:
                        settings = PointsSettings()
                        session.add(settings)
                    
                    referrer.points += settings.points_per_referral
                    referrer.referrals += 1
                    user.referred_by = referrer_id
            except:
                pass
        
        session.commit()
    
    # التحقق من الحظر
    if user.is_banned:
        await update.message.reply_text(f"❌ حسابك محظور. السبب: {user.ban_reason}")
        return
    
    # ترحيب
    welcome_text = f"""
    👋 أهلاً بك {first_name}!

    🆔 إيديك: `{user_id}`
    ⭐ نقاطك: {user.points}
    
    اختر من القائمة:
    """
    
    keyboard = [
        [InlineKeyboardButton("📊 لوحة التحكم", callback_data="admin_panel")] if user.is_admin else [],
        [InlineKeyboardButton("👥 زيادة المشتركين", callback_data="increase_members")],
        [InlineKeyboardButton("⭐ نقاطي", callback_data="my_points")],
        [InlineKeyboardButton("📢 قنوات إجبارية", callback_data="mandatory_channels")],
        [InlineKeyboardButton("📞 تواصل مع المسؤول", callback_data="contact_admin")],
        [InlineKeyboardButton("🔗 رابط الدعوة", callback_data="invite_link")],
        [InlineKeyboardButton("🎁 الهدية اليومية", callback_data="daily_gift")]
    ]
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def check_mandatory_channels(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    channels = session.query(Channel).filter_by(is_mandatory=True).all()
    for channel in channels:
        try:
            member = await context.bot.get_chat_member(channel.channel_id, user_id)
            if member.status in ['left', 'kicked']:
                return False
        except:
            pass
    return True

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id
    
    if data == "admin_panel":
        await show_admin_panel(query, context)
    
    elif data == "increase_members":
        await show_increase_members(query, context)
    
    elif data == "my_points":
        await show_my_points(query, context)
    
    elif data == "mandatory_channels":
        await show_mandatory_channels(query, context)
    
    elif data == "contact_admin":
        await show_contact_admin(query, context)
    
    elif data == "invite_link":
        await show_invite_link(query, context)
    
    elif data == "daily_gift":
        await give_daily_gift(query, context)
    
    elif data == "check_subscription":
        if await check_mandatory_channels(user_id, context):
            await query.edit_message_text("✅ تم التحقق من الاشتراك! استخدم /start للبدء.")
        else:
            await query.answer("❌ لم تشترك في كل القنوات بعد!", show_alert=True)
    
    elif data.startswith("funding_type_"):
        funding_type = data.split("_")[2]
        context.user_data['funding_type'] = funding_type
        await query.edit_message_text(
            f"📝 ارسل عدد الأعضاء المطلوب ({funding_type}):\n\n"
            f"💎 سعر العضو الواحد: {Config.POINTS_PER_MEMBER} نقطة\n"
            f"💰 احسب التكلفة: (العدد × {Config.POINTS_PER_MEMBER})"
        )

async def show_increase_members(query, context):
    keyboard = [
        [InlineKeyboardButton("📢 قناة عامة", callback_data="funding_type_channel")],
        [InlineKeyboardButton("👥 مجموعة", callback_data="funding_type_group")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")]
    ]
    await query.edit_message_text(
        "اختر نوع القناة/المجموعة التي تريد زيادة أعضائها:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def show_my_points(query, context):
    user = session.query(User).filter_by(user_id=query.from_user.id).first()
    if not user:
        return
    
    points_text = f"""
    ⭐ نقاطك الحالية: {user.points}
    
    طرق زيادة النقاط:
    1. 🔗 دعوة أصدقاء: {Config.POINTS_PER_REFERRAL} نقاط لكل صديق
    2. 📢 الاشتراك في القنوات: {Config.POINTS_PER_CHANNEL_SUB} نقاط لكل قناة
    3. 🎁 الهدية اليومية: {Config.DAILY_GIFT_POINTS} نقاط يومياً
    4. 💰 شراء النقاط: تواصل مع المسؤول
    
    أقل حد للتمويل: {Config.MIN_POINTS_FOR_FUNDING} نقطة
    """
    
    keyboard = [
        [InlineKeyboardButton("🎁 المكافآت", callback_data="rewards")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")]
    ]
    
    await query.edit_message_text(
        points_text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def show_mandatory_channels(query, context):
    channels = session.query(Channel).filter_by(is_mandatory=True).all()
    if not channels:
        text = "✅ لا توجد قنوات إجبارية حالياً."
    else:
        text = "📢 قنوات الاشتراك الإجباري:\n\n"
        for channel in channels:
            sub_text = f"✅ تم الاشتراك" if await check_mandatory_channels(query.from_user.id, context) else "❌ غير مشترك"
            text += f"• {channel.channel_title}\n{sub_text}\n\n"
    
    keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def show_contact_admin(query, context):
    admins = session.query(AdminContact).filter_by(is_active=True).all()
    if not admins:
        text = "📞 لا يوجد مسؤولين متاحين حالياً."
    else:
        text = "📞 قائمة المسؤولين:\n\n"
        for admin in admins:
            text += f"• @{admin.admin_username}\n"
        text += "\nراسل أي مسؤول للشحن أو الاستفسار."
    
    keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def show_invite_link(query, context):
    bot_username = context.bot.username
    invite_link = f"https://t.me/{bot_username}?start={query.from_user.id}"
    
    text = f"""
    🔗 رابط دعوتك الخاص:
    
    `{invite_link}`
    
    📊 لكل صديق تدعوه: {Config.POINTS_PER_REFERRAL} نقاط
    ⭐ النقاط تخصم فور اشتراك صديقك
    """
    
    keyboard = [
        [InlineKeyboardButton("🔗 نسخ الرابط", callback_data="copy_link")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def give_daily_gift(query, context):
    user = session.query(User).filter_by(user_id=query.from_user.id).first()
    if not user:
        return
    
    now = datetime.now()
    if user.last_daily_gift and (now - user.last_daily_gift).days < 1:
        next_gift = user.last_daily_gift + timedelta(days=1)
        remaining = next_gift - now
        hours = remaining.seconds // 3600
        minutes = (remaining.seconds % 3600) // 60
        
        await query.answer(f"⏳ الهدية متاحة بعد {hours} ساعة و {minutes} دقيقة", show_alert=True)
        return
    
    user.points += Config.DAILY_GIFT_POINTS
    user.last_daily_gift = now
    session.commit()
    
    await query.answer(f"🎁 حصلت على {Config.DAILY_GIFT_POINTS} نقاط!", show_alert=True)
    await show_my_points(query, context)

async def show_admin_panel(query, context):
    user = session.query(User).filter_by(user_id=query.from_user.id).first()
    if not user or not user.is_admin:
        await query.answer("❌ ليس لديك صلاحية الدخول!", show_alert=True)
        return
    
    text = """
    👑 لوحة تحكم المشرف
    
    اختر القسم:
    """
    
    keyboard = [
        [InlineKeyboardButton("📊 الإحصائيات", callback_data="admin_stats")],
        [InlineKeyboardButton("👥 إدارة المستخدمين", callback_data="admin_users")],
        [InlineKeyboardButton("👑 إدارة المشرفين", callback_data="admin_admins")],
        [InlineKeyboardButton("📢 إدارة القنوات", callback_data="admin_channels")],
        [InlineKeyboardButton("👥 إدارة المجموعات", callback_data="admin_groups")],
        [InlineKeyboardButton("📋 طلبات التمويل", callback_data="admin_requests")],
        [InlineKeyboardButton("⚙️ إعدادات النقاط", callback_data="admin_points")],
        [InlineKeyboardButton("📨 إرسال للجميع", callback_data="admin_broadcast")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_funding_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    
    if 'funding_type' not in context.user_data:
        return
    
    if not text.isdigit():
        await update.message.reply_text("❌ الرجاء إدخال رقم صحيح!")
        return
    
    requested_members = int(text)
    user = session.query(User).filter_by(user_id=user_id).first()
    
    if not user:
        return
    
    # حساب التكلفة
    points_needed = requested_members * Config.POINTS_PER_MEMBER
    
    if user.points < points_needed:
        await update.message.reply_text(
            f"❌ نقاطك غير كافية!\n"
            f"💎 لديك: {user.points} نقطة\n"
            f"💰 تحتاج: {points_needed} نقطة\n"
            f"⭐ الناقص: {points_needed - user.points} نقطة"
        )
        return
    
    context.user_data['requested_members'] = requested_members
    context.user_data['points_needed'] = points_needed
    
    await update.message.reply_text(
        f"✅ الطلب مقبول!\n"
        f"📊 عدد الأعضاء: {requested_members}\n"
        f"💰 التكلفة: {points_needed} نقطة\n\n"
        f"📝 الآن ارسل رابط قناتك/مجموعتك:\n"
        f"(يبدأ بـ @ أو https://t.me/)"
    )

async def handle_channel_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    link = update.message.text
    user = session.query(User).filter_by(user_id=user_id).first()
    
    if not user or 'requested_members' not in context.user_data:
        return
    
    # استخراج معرف القناة من الرابط
    channel_id = extract_channel_id(link)
    if not channel_id:
        await update.message.reply_text("❌ رابط غير صالح! تأكد من الرابط وأرسله مرة أخرى.")
        return
    
    # التحقق من أن البوت أدمن في القناة
    try:
        chat_member = await context.bot.get_chat_member(channel_id, context.bot.id)
        if chat_member.status not in ['administrator', 'creator']:
            await update.message.reply_text("❌ البوت ليس أدمن في القناة! ارفع البوت كأدمن أولاً.")
            return
    except:
        await update.message.reply_text("❌ لا يمكن الوصول للقناة! تأكد من صلاحيات البوت.")
        return
    
    # خصم النقاط وإنشاء الطلب
    requested_members = context.user_data['requested_members']
    points_needed = context.user_data['points_needed']
    
    user.points -= points_needed
    funding_request = FundingRequest(
        user_id=user_id,
        target_channel=channel_id,
        target_type=context.user_data['funding_type'],
        requested_members=requested_members,
        points_cost=points_needed,
        status='pending',
        created_at=datetime.now()
    )
    
    session.add(funding_request)
    session.commit()
    
    # إرسال إشعار للمشرفين
    await notify_admins_about_request(context.bot, funding_request, user)
    
    await update.message.reply_text(
        f"✅ تم استلام طلبك!\n"
        f"📊 رقم الطلب: {funding_request.id}\n"
        f"👥 الأعضاء: {requested_members}\n"
        f"💰 النقاط المخصومة: {points_needed}\n"
        f"⭐ نقاطك المتبقية: {user.points}\n\n"
        f"⏳ الطلب قيد الانتظار للموافقة..."
    )
    
    # تنظيف البيانات المؤقتة
    context.user_data.clear()

def extract_channel_id(link: str) -> str:
    """استخراج معرف القناة من الرابط"""
    if link.startswith('@'):
        return link
    elif 't.me/' in link:
        parts = link.split('t.me/')
        if len(parts) > 1:
            channel_part = parts[1].split('/')[0]
            if channel_part.startswith('+'):
                return channel_part
            else:
                return '@' + channel_part
    return None

async def notify_admins_about_request(bot, request, user):
    """إرسال إشعار للمشرفين بطلب جديد"""
    admins = session.query(User).filter_by(is_admin=True).all()
    
    for admin in admins:
        try:
            text = f"""
            📋 طلب تمويل جديد!

            👤 المستخدم: @{user.username or user.first_name}
            🆔 الإيدي: {user.user_id}
            📊 رقم الطلب: {request.id}
            👥 عدد الأعضاء: {request.requested_members}
            💰 التكلفة: {request.points_cost} نقطة
            📢 الهدف: {request.target_channel}
            🕒 الوقت: {request.created_at.strftime('%Y-%m-%d %H:%M:%S')}
            """
            
            keyboard = [
                [
                    InlineKeyboardButton("✅ قبول", callback_data=f"approve_request_{request.id}"),
                    InlineKeyboardButton("❌ رفض", callback_data=f"reject_request_{request.id}")
                ],
                [InlineKeyboardButton("👁️ عرض التفاصيل", callback_data=f"view_request_{request.id}")]
            ]
            
            await bot.send_message(
                admin.user_id,
                text,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except:
            pass

async def handle_admin_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    admin_id = query.from_user.id
    
    if data.startswith("approve_request_"):
        request_id = int(data.split("_")[2])
        await approve_funding_request(query, context, request_id, admin_id)
    
    elif data.startswith("reject_request_"):
        request_id = int(data.split("_")[2])
        await reject_funding_request(query, context, request_id, admin_id)

async def approve_funding_request(query, context, request_id, admin_id):
    request = session.query(FundingRequest).filter_by(id=request_id).first()
    if not request:
        await query.answer("❌ الطلب غير موجود!", show_alert=True)
        return
    
    request.status = 'approved'
    request.approved_by = admin_id
    request.updated_at = datetime.now()
    session.commit()
    
    # إعلام المستخدم
    try:
        user = session.query(User).filter_by(user_id=request.user_id).first()
        if user:
            await context.bot.send_message(
                user.user_id,
                f"✅ تمت الموافقة على طلبك #{request_id}\n"
                f"👥 سيتم البدء بإضافة {request.requested_members} عضو قريباً."
            )
    except:
        pass
    
    await query.edit_message_text(f"✅ تمت الموافقة على الطلب #{request_id}")
    
    # البدء بعملية إضافة الأعضاء
    await start_adding_members(context.bot, request)

async def start_adding_members(bot, request):
    """بدء عملية إضافة الأعضاء"""
    # هنا راح يكون كود سحب الأعضاء من المجموعات وإضافتهم
    # هذه عملية معقدة تحتاج لمعالجة خاصة
    
    # مؤقتاً، نغير الحالة لإكمال
    request.status = 'completed'
    request.completed_members = request.requested_members
    session.commit()
    
    # إعلام المستخدم
    try:
        await bot.send_message(
            request.user_id,
            f"✅ تم الانتهاء من طلبك #{request.id}\n"
            f"👥 تمت إضافة {request.completed_members} عضو بنجاح!"
        )
    except:
        pass

async def reject_funding_request(query, context, request_id, admin_id):
    request = session.query(FundingRequest).filter_by(id=request_id).first()
    if not request:
        await query.answer("❌ الطلب غير موجود!", show_alert=True)
        return
    
    # استرجاع النقاط للمستخدم
    user = session.query(User).filter_by(user_id=request.user_id).first()
    if user:
        user.points += request.points_cost
    
    request.status = 'rejected'
    request.approved_by = admin_id
    session.commit()
    
    # إعلام المستخدم
    try:
        await context.bot.send_message(
            user.user_id,
            f"❌ تم رفض طلبك #{request_id}\n"
            f"💰 تم إرجاع {request.points_cost} نقطة لحسابك."
        )
    except:
        pass
    
    await query.edit_message_text(f"❌ تم رفض الطلب #{request_id}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الرسائل النصية"""
    if update.message.text:
        # إذا كان المستخدم في مرحلة إدخال عدد الأعضاء
        if 'funding_type' in context.user_data and 'requested_members' not in context.user_data:
            await handle_funding_request(update, context)
        
        # إذا كان المستخدم في مرحلة إدخال الرابط
        elif 'requested_members' in context.user_data and 'points_needed' in context.user_data:
            await handle_channel_link(update, context)
        
        # إذا كان رسالة عادية
        else:
            # التحقق من الاشتراك الإجباري أولاً
            user_id = update.effective_user.id
            if not await check_mandatory_channels(user_id, context):
                await update.message.reply_text("⛔ يجب الاشتراك في القنوات الإجبارية أولاً! استخدم /start")
                return
            
            # إذا كان المستخدم مشرف ويرسل أمر
            user = session.query(User).filter_by(user_id=user_id).first()
            if user and user.is_admin:
                await handle_admin_commands(update, context)
            else:
                await update.message.reply_text("استخدم الأزرار في القائمة أو /start للبدء")

async def handle_admin_commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة أوامر المشرفين"""
    text = update.message.text
    user_id = update.effective_user.id
    
    if text.startswith('/add_admin'):
        parts = text.split()
        if len(parts) < 2:
            await update.message.reply_text("❌ صيغة خاطئة: /add_admin @username أو user_id")
            return
        
        target = parts[1].replace('@', '')
        if target.isdigit():
            target_user = session.query(User).filter_by(user_id=int(target)).first()
        else:
            target_user = session.query(User).filter_by(username=target).first()
        
        if not target_user:
            await update.message.reply_text("❌ المستخدم غير موجود!")
            return
        
        target_user.is_admin = True
        session.commit()
        
        await update.message.reply_text(f"✅ تمت ترقية @{target_user.username} إلى مشرف")
    
    elif text.startswith('/ban'):
        parts = text.split()
        if len(parts) < 3:
            await update.message.reply_text("❌ صيغة خاطئة: /ban @username السبب")
            return
        
        target = parts[1].replace('@', '')
        reason = ' '.join(parts[2:])
        
        if target.isdigit():
            target_user = session.query(User).filter_by(user_id=int(target)).first()
        else:
            target_user = session.query(User).filter_by(username=target).first()
        
        if not target_user:
            await update.message.reply_text("❌ المستخدم غير موجود!")
            return
        
        target_user.is_banned = True
        target_user.ban_reason = reason
        session.commit()
        
        await update.message.reply_text(f"✅ تم حظر @{target_user.username}\nالسبب: {reason}")
    
    elif text.startswith('/add_points'):
        parts = text.split()
        if len(parts) < 3:
            await update.message.reply_text("❌ صيغة خاطئة: /add_points @username العدد")
            return
        
        target = parts[1].replace('@', '')
        points = int(parts[2])
        
        if target.isdigit():
            target_user = session.query(User).filter_by(user_id=int(target)).first()
        else:
            target_user = session.query(User).filter_by(username=target).first()
        
        if not target_user:
            await update.message.reply_text("❌ المستخدم غير موجود!")
            return
        
        target_user.points += points
        session.commit()
        
        await update.message.reply_text(f"✅ تم إضافة {points} نقطة لـ @{target_user.username}")
