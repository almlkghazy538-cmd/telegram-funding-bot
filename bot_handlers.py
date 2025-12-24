from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, MessageHandler, filters
from database import get_db, User, Channel, FundingRequest, PointsSettings, SystemSettings, PointsTransfer
from config import Config
from datetime import datetime, timedelta

# ==================== دوال المساعدة ====================
async def check_mandatory_channels(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """التحقق من اشتراك المستخدم في القنوات الإجبارية"""
    db = get_db()
    try:
        channels = db.query(Channel).filter_by(is_mandatory=True).all()
        for channel in channels:
            try:
                member = await context.bot.get_chat_member(channel.channel_id, user_id)
                if member.status in ['left', 'kicked']:
                    return False
            except:
                continue
        return True
    finally:
        db.close()

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

# ==================== معالجة الأوامر ====================
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة أمر /start"""
    user_id = update.effective_user.id
    db = get_db()
    
    try:
        # التحقق من وضع الصيانة
        settings = db.query(SystemSettings).first()
        if settings and settings.maintenance_mode:
            await update.message.reply_text(f"🔧 {settings.maintenance_message}")
            return
        
        # التحقق من الاشتراك الإجباري
        if not await check_mandatory_channels(user_id, context):
            channels = db.query(Channel).filter_by(is_mandatory=True).all()
            if channels:
                keyboard = []
                for channel in channels:
                    if channel.channel_username:
                        username = channel.channel_username.replace('@', '')
                        keyboard.append([
                            InlineKeyboardButton(
                                f"اشترك في {channel.channel_title or username}",
                                url=f"https://t.me/{username}"
                            )
                        ])
                keyboard.append([InlineKeyboardButton("✅ تحقق من الاشتراك", callback_data="check_subscription")])
                
                await update.message.reply_text(
                    "⚠️ يجب الاشتراك في القنوات التالية أولاً:",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            return
        
        # تسجيل/جلب المستخدم
        user = db.query(User).filter_by(user_id=user_id).first()
        if not user:
            user = User(
                user_id=user_id,
                username=update.effective_user.username or "",
                first_name=update.effective_user.first_name or "",
                last_name=update.effective_user.last_name or "",
                created_at=datetime.now()
            )
            
            # معالجة الإحالة
            if context.args:
                try:
                    referrer_id = int(context.args[0])
                    referrer = db.query(User).filter_by(user_id=referrer_id).first()
                    if referrer and referrer_id != user_id:
                        points_settings = db.query(PointsSettings).first()
                        if points_settings:
                            referrer.points += points_settings.points_per_referral
                            referrer.referrals += 1
                            user.referred_by = referrer_id
                except:
                    pass
            
            db.add(user)
            db.commit()
        
        # التحقق من الحظر
        if user.is_banned:
            await update.message.reply_text(f"❌ حسابك محظور. السبب: {user.ban_reason}")
            return
        
        # عرض القائمة الرئيسية
        await show_main_menu(update, context, user)
        
    except Exception as e:
        print(f"Error in start_command: {e}")
    finally:
        db.close()

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, user):
    """عرض القائمة الرئيسية"""
    welcome_text = f"""
👋 أهلاً بك {user.first_name}!

🆔 إيديك: `{user.user_id}`
⭐ نقاطك: {user.points}

اختر من القائمة:
"""
    
    keyboard = []
    if user.is_admin:
        keyboard.append([InlineKeyboardButton("👑 لوحة التحكم", callback_data="admin_panel")])
    
    keyboard.extend([
        [InlineKeyboardButton("👥 زيادة المشتركين", callback_data="increase_members")],
        [InlineKeyboardButton("⭐ نقاطي", callback_data="my_points")],
        [InlineKeyboardButton("🔄 تحويل النقاط", callback_data="transfer_points")],
        [InlineKeyboardButton("📢 قنوات إجبارية", callback_data="mandatory_channels")],
        [InlineKeyboardButton("📞 تواصل مع المسؤول", callback_data="contact_admin")],
        [InlineKeyboardButton("🔗 رابط الدعوة", callback_data="invite_link")],
        [InlineKeyboardButton("🎁 الهدية اليومية", callback_data="daily_gift")],
        [InlineKeyboardButton("📋 طلباتي", callback_data="my_requests")]
    ])
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            welcome_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            welcome_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

# ==================== معالجة الأزرار ====================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة ضغطات الأزرار"""
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id
    db = get_db()
    
    try:
        # التحقق من وضع الصيانة
        settings = db.query(SystemSettings).first()
        if settings and settings.maintenance_mode and not data.startswith("admin_"):
            await query.message.reply_text(f"🔧 {settings.maintenance_message}")
            return
        
        if data == "admin_panel":
            user = db.query(User).filter_by(user_id=user_id).first()
            if user and user.is_admin:
                await show_admin_panel(query, context)
            else:
                await query.answer("❌ ليس لديك صلاحية!", show_alert=True)
        elif data == "increase_members":
            await show_increase_members(query, context)
        elif data == "my_points":
            await show_my_points(query, context)
        elif data == "transfer_points":
            await show_transfer_points(query, context)
        elif data == "mandatory_channels":
            await show_mandatory_channels_menu(query, context)
        elif data == "contact_admin":
            await show_contact_admin(query, context)
        elif data == "invite_link":
            await show_invite_link(query, context)
        elif data == "daily_gift":
            await give_daily_gift(query, context)
        elif data == "my_requests":
            await show_my_requests(query, context)
        elif data == "check_subscription":
            if await check_mandatory_channels(user_id, context):
                user = db.query(User).filter_by(user_id=user_id).first()
                if user:
                    await show_main_menu(update, context, user)
            else:
                await query.answer("❌ لم تشترك في كل القنوات بعد!", show_alert=True)
        elif data == "back_to_main":
            user = db.query(User).filter_by(user_id=user_id).first()
            if user:
                await show_main_menu(update, context, user)
        elif data.startswith("funding_type_"):
            funding_type = data.split("_")[2]
            context.user_data['funding_type'] = funding_type
            points_settings = db.query(PointsSettings).first()
            points_per_member = points_settings.points_per_member if points_settings else Config.POINTS_PER_MEMBER
            
            await query.edit_message_text(
                f"📝 ارسل عدد الأعضاء المطلوب ({funding_type}):\n\n"
                f"💎 سعر العضو الواحد: {points_per_member} نقطة\n"
                f"💰 احسب التكلفة: (العدد × {points_per_member})"
            )
        elif data == "start_transfer":
            await query.edit_message_text(
                "🔄 تحويل النقاط\n\n"
                "ارسل رسالة بالشكل التالي:\n"
                "`تحويل [المبلغ] [إيدي المستخدم]`\n\n"
                "مثال: `تحويل 100 123456789`\n\n"
                "💡 عمولة التحويل: 5% (قابلة للتغيير من لوحة التحكم)"
            )
        elif data == "transfer_history":
            await show_transfer_history(query, context)
        
    finally:
        db.close()

# ==================== دوال العرض ====================
async def show_increase_members(query, context):
    """عرض واجهة زيادة الأعضاء"""
    db = get_db()
    try:
        user = db.query(User).filter_by(user_id=query.from_user.id).first()
        if not user:
            return
        
        points_settings = db.query(PointsSettings).first()
        min_points = points_settings.min_points_for_funding if points_settings else Config.MIN_POINTS_FOR_FUNDING
        
        if user.points < min_points:
            await query.answer(f"❌ تحتاج على الأقل {min_points} نقطة لطلب التمويل!", show_alert=True)
            return
        
        keyboard = [
            [InlineKeyboardButton("📢 قناة عامة", callback_data="funding_type_channel")],
            [InlineKeyboardButton("👥 مجموعة", callback_data="funding_type_group")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")]
        ]
        
        await query.edit_message_text(
            "اختر نوع القناة/المجموعة التي تريد زيادة أعضائها:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    finally:
        db.close()

async def show_my_points(query, context):
    """عرض نقاط المستخدم"""
    db = get_db()
    try:
        user = db.query(User).filter_by(user_id=query.from_user.id).first()
        if not user:
            return
        
        points_settings = db.query(PointsSettings).first()
        
        points_text = f"""
⭐ نقاطك الحالية: {user.points}

طرق زيادة النقاط:
1. 🔗 دعوة أصدقاء: {points_settings.points_per_referral if points_settings else 5} نقاط لكل صديق
2. 📢 الاشتراك في القنوات: {points_settings.points_per_channel if points_settings else 2} نقاط لكل قناة
3. 🎁 الهدية اليومية: {points_settings.daily_gift_points if points_settings else 3} نقاط يومياً
4. 💰 شراء النقاط: تواصل مع المسؤول

أقل حد للتمويل: {points_settings.min_points_for_funding if points_settings else 25} نقطة
"""
        
        keyboard = [
            [InlineKeyboardButton("🔄 تحويل النقاط", callback_data="transfer_points")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")]
        ]
        
        await query.edit_message_text(
            points_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    finally:
        db.close()

async def show_transfer_points(query, context):
    """عرض واجهة تحويل النقاط"""
    db = get_db()
    try:
        settings = db.query(SystemSettings).first()
        if not settings or not settings.transfer_enabled:
            await query.answer("❌ خدمة تحويل النقاط معطلة حالياً!", show_alert=True)
            return
        
        user = db.query(User).filter_by(user_id=query.from_user.id).first()
        if not user:
            return
        
        keyboard = [
            [InlineKeyboardButton("🚀 بدء التحويل", callback_data="start_transfer")],
            [InlineKeyboardButton("📋 سجل التحويلات", callback_data="transfer_history")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")]
        ]
        
        await query.edit_message_text(
            f"🔄 تحويل النقاط\n\n"
            f"⭐ نقاطك الحالية: {user.points}\n"
            f"💸 عمولة التحويل: {settings.transfer_fee_percent}%\n"
            f"📤 أقصى مبلغ للتحويل: لا يوجد حد\n\n"
            f"اختر الإجراء:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    finally:
        db.close()

async def show_transfer_history(query, context):
    """عرض سجل تحويلات المستخدم"""
    db = get_db()
    try:
        user_id = query.from_user.id
        transfers = db.query(PointsTransfer).filter(
            (PointsTransfer.from_user_id == user_id) | (PointsTransfer.to_user_id == user_id)
        ).order_by(PointsTransfer.transfer_date.desc()).limit(10).all()
        
        if not transfers:
            text = "📋 لا توجد تحويلات سابقة."
        else:
            text = "📋 آخر 10 تحويلات:\n\n"
            for transfer in transfers:
                if transfer.from_user_id == user_id:
                    direction = "📤 مرسل"
                    target = transfer.to_user_id
                else:
                    direction = "📥 مستلم"
                    target = transfer.from_user_id
                
                text += (
                    f"{direction}\n"
                    f"💰 المبلغ: {transfer.amount} نقطة\n"
                    f"💸 العمولة: {transfer.fee_amount} نقطة\n"
                    f"👤 الطرف الآخر: {target}\n"
                    f"🕒 الوقت: {transfer.transfer_date.strftime('%Y-%m-%d %H:%M')}\n"
                    f"────────────────────\n"
                )
        
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="transfer_points")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    finally:
        db.close()

async def show_mandatory_channels_menu(query, context):
    """عرض قنوات الاشتراك الإجباري"""
    db = get_db()
    try:
        channels = db.query(Channel).filter_by(is_mandatory=True).all()
        
        if not channels:
            text = "✅ لا توجد قنوات إجبارية حالياً."
        else:
            text = "📢 قنوات الاشتراك الإجباري:\n\n"
            for i, channel in enumerate(channels, 1):
                is_subscribed = await check_mandatory_channels(query.from_user.id, context)
                status = "✅ مشترك" if is_subscribed else "❌ غير مشترك"
                username = channel.channel_username or channel.channel_id
                text += f"{i}. {channel.channel_title or username}\n{status}\n\n"
        
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    finally:
        db.close()

async def show_contact_admin(query, context):
    """عرض جهات اتصال المسؤولين"""
    db = get_db()
    try:
        admins = db.query(User).filter_by(is_admin=True).all()
        
        if not admins:
            text = "📞 لا يوجد مسؤولين متاحين حالياً."
        else:
            text = "📞 قائمة المسؤولين:\n\n"
            for admin in admins:
                username = admin.username or f"المستخدم {admin.user_id}"
                text += f"• {username} - إيدي: {admin.user_id}\n"
            text += "\nراسل أي مسؤول للشحن أو الاستفسار."
        
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    finally:
        db.close()

async def show_invite_link(query, context):
    """عرض رابط الدعوة"""
    bot_username = context.bot.username
    invite_link = f"https://t.me/{bot_username}?start={query.from_user.id}"
    
    db = get_db()
    try:
        points_settings = db.query(PointsSettings).first()
        points_per_referral = points_settings.points_per_referral if points_settings else Config.POINTS_PER_REFERRAL
        
        text = f"""
🔗 رابط دعوتك الخاص:

`{invite_link}`

📊 لكل صديق تدعوه: {points_per_referral} نقاط
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
    finally:
        db.close()

async def show_my_requests(query, context):
    """عرض طلبات المستخدم"""
    db = get_db()
    try:
        requests = db.query(FundingRequest).filter_by(user_id=query.from_user.id).order_by(FundingRequest.created_at.desc()).limit(5).all()
        
        if not requests:
            text = "📋 لا توجد طلبات سابقة."
        else:
            text = "📋 آخر 5 طلبات:\n\n"
            for req in requests:
                status_emoji = {
                    'pending': '⏳',
                    'approved': '✅',
                    'completed': '🎉',
                    'rejected': '❌'
                }.get(req.status, '📝')
                
                text += (
                    f"طلب #{req.id}\n"
                    f"{status_emoji} الحالة: {req.status}\n"
                    f"👥 الأعضاء: {req.requested_members}\n"
                    f"💰 التكلفة: {req.points_cost} نقطة\n"
                    f"🕒 الوقت: {req.created_at.strftime('%Y-%m-%d %H:%M')}\n"
                    f"────────────────────\n"
                )
        
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    finally:
        db.close()

async def give_daily_gift(query, context):
    """منح الهدية اليومية"""
    db = get_db()
    try:
        user = db.query(User).filter_by(user_id=query.from_user.id).first()
        if not user:
            return
        
        now = datetime.now()
        
        # التحقق إذا أخذ الهدية اليوم
        if user.last_daily_gift:
            last_gift_date = user.last_daily_gift.date()
            if last_gift_date == now.date():
                next_gift = user.last_daily_gift + timedelta(days=1)
                remaining = next_gift - now
                hours = remaining.seconds // 3600
                minutes = (remaining.seconds % 3600) // 60
                
                await query.answer(f"⏳ الهدية متاحة بعد {hours} ساعة و {minutes} دقيقة", show_alert=True)
                return
        
        # منح النقاط
        points_settings = db.query(PointsSettings).first()
        points = points_settings.daily_gift_points if points_settings else Config.DAILY_GIFT_POINTS
        
        user.points += points
        user.last_daily_gift = now
        db.commit()
        
        await query.answer(f"🎁 حصلت على {points} نقاط!", show_alert=True)
        await show_my_points(query, context)
    finally:
        db.close()

async def show_admin_panel(query, context):
    """عرض لوحة تحكم المشرف"""
    db = get_db()
    try:
        user = db.query(User).filter_by(user_id=query.from_user.id).first()
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
            [InlineKeyboardButton("⚙️ إعدادات النظام", callback_data="admin_system")],
            [InlineKeyboardButton("⭐ إعدادات النقاط", callback_data="admin_points")],
            [InlineKeyboardButton("🔄 إعدادات التحويل", callback_data="admin_transfer")],
            [InlineKeyboardButton("📨 إرسال للجميع", callback_data="admin_broadcast")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")]
        ]
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    finally:
        db.close()

# ==================== معالجة الرسائل النصية ====================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الرسائل النصية"""
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    # التحقق من وضع الصيانة
    db = get_db()
    try:
        settings = db.query(SystemSettings).first()
        if settings and settings.maintenance_mode:
            # استثناء: يمكن للمشرفين استخدام الأوامر أثناء الصيانة
            user = db.query(User).filter_by(user_id=user_id).first()
            if not user or not user.is_admin:
                await update.message.reply_text(f"🔧 {settings.maintenance_message}")
                return
        
        # إذا كان المستخدم في مرحلة إدخال عدد الأعضاء
        if 'funding_type' in context.user_data and 'requested_members' not in context.user_data:
            await handle_funding_request(update, context)
        
        # إذا كان المستخدم في مرحلة إدخال الرابط
        elif 'requested_members' in context.user_data and 'points_needed' in context.user_data:
            await handle_channel_link(update, context)
        
        # إذا كان طلب تحويل نقاط
        elif text.startswith('تحويل '):
            await handle_points_transfer(update, context)
        
        # إذا كان رسالة عادية
        else:
            # التحقق من الاشتراك الإجباري أولاً
            if not await check_mandatory_channels(user_id, context):
                await update.message.reply_text("⛔ يجب الاشتراك في القنوات الإجبارية أولاً! استخدم /start")
                return
            
            # إذا كان المستخدم مشرف ويرسل أمر
            user = db.query(User).filter_by(user_id=user_id).first()
            if user and user.is_admin and text.startswith('/'):
                await handle_admin_commands(update, context)
            else:
                await update.message.reply_text("استخدم الأزرار في القائمة أو /start للبدء")
    
    finally:
        db.close()

async def handle_funding_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة طلب التمويل"""
    user_id = update.effective_user.id
    text = update.message.text
    
    if not text.isdigit():
        await update.message.reply_text("❌ الرجاء إدخال رقم صحيح!")
        return
    
    requested_members = int(text)
    db = get_db()
    
    try:
        user = db.query(User).filter_by(user_id=user_id).first()
        if not user:
            return
        
        points_settings = db.query(PointsSettings).first()
        points_per_member = points_settings.points_per_member if points_settings else Config.POINTS_PER_MEMBER
        
        # حساب التكلفة
        points_needed = requested_members * points_per_member
        
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
    finally:
        db.close()

async def handle_channel_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة رابط القناة"""
    user_id = update.effective_user.id
    link = update.message.text
    db = get_db()
    
    try:
        user = db.query(User).filter_by(user_id=user_id).first()
        if not user or 'requested_members' not in context.user_data:
            return
        
        # استخراج معرف القناة
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
        except Exception as e:
            print(f"Error checking admin status: {e}")
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
        
        db.add(funding_request)
        db.commit()
        
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
        
    finally:
        db.close()

async def handle_points_transfer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة طلب تحويل النقاط"""
    user_id = update.effective_user.id
    text = update.message.text.strip()
    db = get_db()
    
    try:
        # التحقق من صيغة الرسالة
        if not text.startswith('تحويل '):
            return
        
        parts = text.split()
        if len(parts) != 3:
            await update.message.reply_text("❌ صيغة خاطئة! استخدم: `تحويل [المبلغ] [إيدي المستخدم]`")
            return
        
        amount = int(parts[1])
        target_user_id = int(parts[2])
        
        # التحقق من الإعدادات
        settings = db.query(SystemSettings).first()
        if not settings or not settings.transfer_enabled:
            await update.message.reply_text("❌ خدمة تحويل النقاط معطلة حالياً!")
            return
        
        # منع التحويل للنفس
        if target_user_id == user_id:
            await update.message.reply_text("❌ لا يمكنك تحويل النقاط لنفسك!")
            return
        
        # جلب بيانات المرسل
        sender = db.query(User).filter_by(user_id=user_id).first()
        if not sender:
            await update.message.reply_text("❌ حسابك غير موجود!")
            return
        
        # التحقق من الرصيد
        fee_percent = settings.transfer_fee_percent
        fee_amount = int(amount * fee_percent / 100)
        total_deduct = amount + fee_amount
        
        if sender.points < total_deduct:
            await update.message.reply_text(
                f"❌ نقاطك غير كافية!\n"
                f"💎 تحتاج: {total_deduct} نقطة (المبلغ + العمولة)\n"
                f"⭐ لديك: {sender.points} نقطة"
            )
            return
        
        # جلب بيانات المستقبل
        receiver = db.query(User).filter_by(user_id=target_user_id).first()
        if not receiver:
            await update.message.reply_text("❌ المستخدم الهدف غير موجود!")
            return
        
        # تنفيذ التحويل
        sender.points -= total_deduct
        receiver.points += amount
        
        # تسجيل العملية
        transfer = PointsTransfer(
            from_user_id=user_id,
            to_user_id=target_user_id,
            amount=amount,
            fee_percent=fee_percent,
            fee_amount=fee_amount,
            net_amount=amount,
            transfer_date=datetime.now()
        )
        db.add(transfer)
        db.commit()
        
        # إرسال إشعارات
        await update.message.reply_text(
            f"✅ تم تحويل {amount} نقطة بنجاح!\n\n"
            f"📤 إلى: {receiver.first_name or 'مستخدم'} (إيدي: {target_user_id})\n"
            f"💸 العمولة: {fee_amount} نقطة ({fee_percent}%)\n"
            f"💰 المبلغ الإجمالي: {total_deduct} نقطة\n"
            f"⭐ رصيدك الجديد: {sender.points} نقطة"
        )
        
        # إشعار المستقبل
        try:
            await context.bot.send_message(
                target_user_id,
                f"🎉 استلمت تحويل نقاط!\n\n"
                f"📥 من: {sender.first_name or 'مستخدم'} (إيدي: {user_id})\n"
                f"💰 المبلغ: {amount} نقطة\n"
                f"⭐ رصيدك الجديد: {receiver.points} نقطة"
            )
        except:
            pass  # قد يكون المستقبل حظر البوت
        
    except ValueError:
        await update.message.reply_text("❌ الرجاء إدخال أرقام صحيحة!")
    except Exception as e:
        await update.message.reply_text(f"❌ حدث خطأ: {str(e)}")
    finally:
        db.close()

async def handle_admin_commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة أوامر المشرفين"""
    text = update.message.text
    user_id = update.effective_user.id
    db = get_db()
    
    try:
        user = db.query(User).filter_by(user_id=user_id).first()
        if not user or not user.is_admin:
            return
        
        if text.startswith('/add_admin'):
            parts = text.split()
            if len(parts) < 2:
                await update.message.reply_text("❌ صيغة خاطئة: /add_admin @username أو user_id")
                return
            
            target = parts[1].replace('@', '')
            if target.isdigit():
                target_user = db.query(User).filter_by(user_id=int(target)).first()
            else:
                target_user = db.query(User).filter_by(username=target).first()
            
            if not target_user:
                await update.message.reply_text("❌ المستخدم غير موجود!")
                return
            
            target_user.is_admin = True
            db.commit()
            
            await update.message.reply_text(f"✅ تمت ترقية {target_user.first_name} إلى مشرف")
        
        elif text.startswith('/ban'):
            parts = text.split()
            if len(parts) < 3:
                await update.message.reply_text("❌ صيغة خاطئة: /ban @username السبب")
                return
            
            target = parts[1].replace('@', '')
            reason = ' '.join(parts[2:])
            
            if target.isdigit():
                target_user = db.query(User).filter_by(user_id=int(target)).first()
            else:
                target_user = db.query(User).filter_by(username=target).first()
            
            if not target_user:
                await update.message.reply_text("❌ المستخدم غير موجود!")
                return
            
            target_user.is_banned = True
            target_user.ban_reason = reason
            db.commit()
            
            await update.message.reply_text(f"✅ تم حظر {target_user.first_name}\nالسبب: {reason}")
        
        elif text.startswith('/add_points'):
            parts = text.split()
            if len(parts) < 3:
                await update.message.reply_text("❌ صيغة خاطئة: /add_points @username العدد")
                return
            
            target = parts[1].replace('@', '')
            points = int(parts[2])
            
            if target.isdigit():
                target_user = db.query(User).filter_by(user_id=int(target)).first()
            else:
                target_user = db.query(User).filter_by(username=target).first()
            
            if not target_user:
                await update.message.reply_text("❌ المستخدم غير موجود!")
                return
            
            target_user.points += points
            db.commit()
            
            await update.message.reply_text(f"✅ تم إضافة {points} نقطة لـ {target_user.first_name}")
        
        elif text.startswith('/maintenance'):
            parts = text.split()
            if len(parts) < 2:
                await update.message.reply_text("❌ صيغة خاطئة: /maintenance on/off")
                return
            
            mode = parts[1].lower()
            settings = db.query(SystemSettings).first()
            if settings:
                if mode == 'on':
                    settings.maintenance_mode = True
                    await update.message.reply_text("✅ تم تفعيل وضع الصيانة")
                elif mode == 'off':
                    settings.maintenance_mode = False
                    await update.message.reply_text("✅ تم تعطيل وضع الصيانة")
                db.commit()
        
        elif text.startswith('/set_fee'):
            parts = text.split()
            if len(parts) < 2:
                await update.message.reply_text("❌ صيغة خاطئة: /set_fee النسبة")
                return
            
            try:
                fee = int(parts[1])
                if fee < 0 or fee > 50:
                    await update.message.reply_text("❌ النسبة يجب أن تكون بين 0 و 50!")
                    return
                
                settings = db.query(SystemSettings).first()
                if settings:
                    old_fee = settings.transfer_fee_percent
                    settings.transfer_fee_percent = fee
                    db.commit()
                    await update.message.reply_text(f"✅ تم تغيير عمولة التحويل من {old_fee}% إلى {fee}%")
            except ValueError:
                await update.message.reply_text("❌ الرجاء إدخال رقم صحيح!")
    
    finally:
        db.close()

async def notify_admins_about_request(bot, request, user):
    """إرسال إشعار للمشرفين بطلب جديد"""
    db = get_db()
    try:
        admins = db.query(User).filter_by(is_admin=True).all()
        
        for admin in admins:
            try:
                text = f"""
📋 طلب تمويل جديد!

👤 المستخدم: {user.first_name or 'مجهول'}
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
                    ]
                ]
                
                await bot.send_message(
                    admin.user_id,
                    text,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            except:
                pass
    finally:
        db.close()
