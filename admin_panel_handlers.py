from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import get_db, User, Channel, GroupSource, FundingRequest, PointsSettings, SystemSettings, PointsTransfer
from datetime import datetime
from sqlalchemy import func, desc

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض إحصائيات النظام"""
    query = update.callback_query
    await query.answer()
    db = get_db()
    
    try:
        # إحصائيات المستخدمين
        total_users = db.query(User).count()
        total_admins = db.query(User).filter_by(is_admin=True).count()
        banned_users = db.query(User).filter_by(is_banned=True).count()
        
        # إحصائيات النقاط
        total_points = db.query(func.sum(User.points)).scalar() or 0
        
        # إحصائيات الطلبات
        total_requests = db.query(FundingRequest).count()
        pending_requests = db.query(FundingRequest).filter_by(status='pending').count()
        completed_requests = db.query(FundingRequest).filter_by(status='completed').count()
        
        # إحصائيات التحويلات
        total_transfers = db.query(PointsTransfer).count()
        
        text = f"""
📊 إحصائيات النظام:

👥 المستخدمين:
• إجمالي المستخدمين: {total_users}
• المشرفين: {total_admins}
• المحظورين: {banned_users}

⭐ النقاط:
• إجمالي النقاط: {total_points:,}

📋 طلبات التمويل:
• إجمالي الطلبات: {total_requests}
• قيد الانتظار: {pending_requests}
• المكتملة: {completed_requests}

🔄 التحويلات:
• عدد التحويلات: {total_transfers}

📢 القنوات والمجموعات:
• القنوات المسجلة: {db.query(Channel).count()}
• مجموعات المصدر: {db.query(GroupSource).count()}
"""
        
        keyboard = [[InlineKeyboardButton("🔙 رجوع للوحة", callback_data="admin_panel")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    finally:
        db.close()

async def admin_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إدارة المستخدمين"""
    query = update.callback_query
    await query.answer()
    
    text = """
👥 إدارة المستخدمين

اختر الإجراء:
"""
    
    keyboard = [
        [InlineKeyboardButton("📋 عرض جميع المستخدمين", callback_data="show_all_users_1")],
        [InlineKeyboardButton("🔍 بحث عن مستخدم", callback_data="search_user_menu")],
        [InlineKeyboardButton("🚫 حظر مستخدم", callback_data="ban_user_menu")],
        [InlineKeyboardButton("✅ فك حظر مستخدم", callback_data="unban_user_menu")],
        [InlineKeyboardButton("⭐ إضافة نقاط", callback_data="add_points_menu")],
        [InlineKeyboardButton("📤 خصم نقاط", callback_data="deduct_points_menu")],
        [InlineKeyboardButton("✉️ إرسال رسالة", callback_data="send_message_menu")],
        [InlineKeyboardButton("🔙 رجوع للوحة", callback_data="admin_panel")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def show_all_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض جميع المستخدمين"""
    query = update.callback_query
    await query.answer()
    
    page = 1
    if query.data.startswith("show_all_users_"):
        try:
            page = int(query.data.split("_")[3])
        except:
            page = 1
    
    db = get_db()
    try:
        # حساب الصفحات
        users_per_page = 10
        total_users = db.query(User).count()
        total_pages = (total_users + users_per_page - 1) // users_per_page
        
        # جلب المستخدمين للصفحة الحالية
        offset = (page - 1) * users_per_page
        users = db.query(User).order_by(User.created_at.desc()).offset(offset).limit(users_per_page).all()
        
        text = f"👥 جميع المستخدمين (الصفحة {page} من {total_pages}):\n\n"
        
        for i, user in enumerate(users, 1):
            status = "🚫" if user.is_banned else "✅"
            admin = "👑" if user.is_admin else ""
            text += f"{offset + i}. {admin} {user.first_name} (@{user.username or 'لا يوجد'})\n"
            text += f"   🆔: {user.user_id} | ⭐: {user.points} | {status}\n"
            text += f"   📅: {user.created_at.strftime('%Y-%m-%d')}\n\n"
        
        # أزرار التنقل بين الصفحات
        keyboard = []
        nav_buttons = []
        
        if page > 1:
            nav_buttons.append(InlineKeyboardButton("◀️ السابق", callback_data=f"show_all_users_{page-1}"))
        
        nav_buttons.append(InlineKeyboardButton(f"📄 {page}/{total_pages}", callback_data="current_page"))
        
        if page < total_pages:
            nav_buttons.append(InlineKeyboardButton("▶️ التالي", callback_data=f"show_all_users_{page+1}"))
        
        if nav_buttons:
            keyboard.append(nav_buttons)
        
        keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="admin_users")])
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    finally:
        db.close()

async def admin_admins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إدارة المشرفين"""
    query = update.callback_query
    await query.answer()
    
    text = """
👑 إدارة المشرفين

اختر الإجراء:
"""
    
    keyboard = [
        [InlineKeyboardButton("➕ إضافة مشرف", callback_data="add_admin_menu")],
        [InlineKeyboardButton("🗑️ إزالة مشرف", callback_data="remove_admin_menu")],
        [InlineKeyboardButton("📋 قائمة المشرفين", callback_data="list_admins")],
        [InlineKeyboardButton("🔙 رجوع للوحة", callback_data="admin_panel")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def list_admins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض قائمة المشرفين"""
    query = update.callback_query
    await query.answer()
    db = get_db()
    
    try:
        admins = db.query(User).filter_by(is_admin=True).order_by(User.created_at).all()
        
        if not admins:
            text = "👑 لا يوجد مشرفين حالياً."
        else:
            text = "👑 قائمة المشرفين:\n\n"
            for i, admin in enumerate(admins, 1):
                text += f"{i}. {admin.first_name} (@{admin.username or 'لا يوجد'})\n"
                text += f"   🆔: {admin.user_id} | 📅: {admin.created_at.strftime('%Y-%m-%d')}\n\n"
        
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="admin_admins")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    finally:
        db.close()

async def admin_channels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إدارة القنوات"""
    query = update.callback_query
    await query.answer()
    
    text = """
📢 إدارة القنوات

اختر الإجراء:
"""
    
    keyboard = [
        [InlineKeyboardButton("➕ إضافة قناة", callback_data="add_channel_menu")],
        [InlineKeyboardButton("🗑️ حذف قناة", callback_data="delete_channel_menu")],
        [InlineKeyboardButton("📋 قائمة القنوات", callback_data="list_channels")],
        [InlineKeyboardButton("🔒 قنوات إجبارية", callback_data="mandatory_channels_menu")],
        [InlineKeyboardButton("🔙 رجوع للوحة", callback_data="admin_panel")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def admin_groups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إدارة المجموعات"""
    query = update.callback_query
    await query.answer()
    
    text = """
👥 إدارة المجموعات المصدر

اختر الإجراء:
"""
    
    keyboard = [
        [InlineKeyboardButton("➕ إضافة مجموعة", callback_data="add_group_menu")],
        [InlineKeyboardButton("🗑️ حذف مجموعة", callback_data="delete_group_menu")],
        [InlineKeyboardButton("📋 قائمة المجموعات", callback_data="list_groups")],
        [InlineKeyboardButton("🔙 رجوع للوحة", callback_data="admin_panel")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def admin_requests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض طلبات التمويل"""
    query = update.callback_query
    await query.answer()
    db = get_db()
    
    try:
        # جلب الطلبات المعلقة
        pending_requests = db.query(FundingRequest).filter_by(status='pending').order_by(FundingRequest.created_at.desc()).limit(10).all()
        
        if not pending_requests:
            text = "✅ لا توجد طلبات معلقة حالياً."
        else:
            text = "📋 طلبات التمويل المعلقة:\n\n"
            for req in pending_requests:
                user = db.query(User).filter_by(user_id=req.user_id).first()
                username = user.first_name if user else "مجهول"
                
                text += f"• #{req.id} - {username}\n"
                text += f"  👥 {req.requested_members} عضو | 💰 {req.points_cost} نقطة\n"
                text += f"  📢 {req.target_channel}\n"
                text += f"  🕒 {req.created_at.strftime('%Y-%m-%d %H:%M')}\n\n"
                
                # أزرار الموافقة/الرفض
                text += f"  [✅](approve_request_{req.id}) [❌](reject_request_{req.id})\n\n"
        
        keyboard = [
            [InlineKeyboardButton("🔄 تحديث", callback_data="admin_requests")],
            [InlineKeyboardButton("📊 جميع الطلبات", callback_data="all_requests")],
            [InlineKeyboardButton("🔙 رجوع للوحة", callback_data="admin_panel")]
        ]
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    finally:
        db.close()

async def admin_system(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إعدادات النظام"""
    query = update.callback_query
    await query.answer()
    db = get_db()
    
    try:
        settings = db.query(SystemSettings).first()
        if not settings:
            settings = SystemSettings()
            db.add(settings)
            db.commit()
        
        text = f"""
⚙️ إعدادات النظام:

🔧 وضع الصيانة: {'✅ مفعل' if settings.maintenance_mode else '❌ معطل'}
📝 رسالة الصيانة: {settings.maintenance_message}

🔄 تحويل النقاط: {'✅ مفعل' if settings.transfer_enabled else '❌ معطل'}
💸 عمولة التحويل: {settings.transfer_fee_percent}%
"""
        
        keyboard = [
            [
                InlineKeyboardButton("🔧 تفعيل/تعطيل الصيانة", callback_data="toggle_maintenance"),
                InlineKeyboardButton("✏️ تعديل رسالة الصيانة", callback_data="edit_maintenance_msg")
            ],
            [
                InlineKeyboardButton("🔄 تفعيل/تعطيل التحويل", callback_data="toggle_transfer"),
                InlineKeyboardButton("💰 تعديل عمولة التحويل", callback_data="edit_transfer_fee")
            ],
            [InlineKeyboardButton("🔙 رجوع للوحة", callback_data="admin_panel")]
        ]
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    finally:
        db.close()

async def admin_points(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إعدادات النقاط"""
    query = update.callback_query
    await query.answer()
    db = get_db()
    
    try:
        settings = db.query(PointsSettings).first()
        if not settings:
            settings = PointsSettings()
            db.add(settings)
            db.commit()
        
        text = f"""
⭐ إعدادات النقاط:

• سعر العضو الواحد: {settings.points_per_member} نقطة
• نقاط الدعوة: {settings.points_per_referral} نقطة
• الهدية اليومية: {settings.daily_gift_points} نقطة
• نقاط الاشتراك: {settings.points_per_channel} نقطة
• الحد الأدنى للتمويل: {settings.min_points_for_funding} نقطة

آخر تحديث: {settings.updated_at.strftime('%Y-%m-%d %H:%M')}
"""
        
        keyboard = [
            [InlineKeyboardButton("✏️ تعديل الإعدادات", callback_data="edit_points_settings")],
            [InlineKeyboardButton("🔙 رجوع للوحة", callback_data="admin_panel")]
        ]
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    finally:
        db.close()

async def admin_transfer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إعدادات التحويل"""
    query = update.callback_query
    await query.answer()
    db = get_db()
    
    try:
        settings = db.query(SystemSettings).first()
        if not settings:
            settings = SystemSettings()
            db.add(settings)
            db.commit()
        
        # إحصائيات التحويلات
        total_transfers = db.query(PointsTransfer).count() or 0
        total_amount = db.query(func.sum(PointsTransfer.amount)).scalar() or 0
        total_fees = db.query(func.sum(PointsTransfer.fee_amount)).scalar() or 0
        
        text = f"""
🔄 إعدادات تحويل النقاط:

📊 الإحصائيات:
• عدد التحويلات: {total_transfers}
• إجمالي المبالغ: {total_amount:,} نقطة
• إجمالي العمولات: {total_fees:,} نقطة

⚙️ الإعدادات الحالية:
• التحويل مفعل: {'✅ نعم' if settings.transfer_enabled else '❌ لا'}
• نسبة العمولة: {settings.transfer_fee_percent}%
"""
        
        keyboard = [
            [
                InlineKeyboardButton("✅ تفعيل التحويل", callback_data="enable_transfer"),
                InlineKeyboardButton("❌ تعطيل التحويل", callback_data="disable_transfer")
            ],
            [InlineKeyboardButton("💰 تعديل العمولة", callback_data="edit_transfer_fee_menu")],
            [InlineKeyboardButton("📋 سجل التحويلات", callback_data="view_transfers_log")],
            [InlineKeyboardButton("🔙 رجوع للوحة", callback_data="admin_panel")]
        ]
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    finally:
        db.close()

async def admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إرسال رسالة للجميع"""
    query = update.callback_query
    await query.answer()
    
    text = """
📨 إرسال رسالة للجميع

⚠️ تحذير: هذه العملية قد تستغرق وقتاً.

اختر نوع الإرسال:
"""
    
    keyboard = [
        [InlineKeyboardButton("📝 رسالة نصية", callback_data="broadcast_text")],
        [InlineKeyboardButton("⭐ رسالة مع نقاط", callback_data="broadcast_with_points")],
        [InlineKeyboardButton("🔙 رجوع للوحة", callback_data="admin_panel")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def toggle_maintenance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تفعيل/تعطيل وضع الصيانة"""
    query = update.callback_query
    await query.answer()
    db = get_db()
    
    try:
        settings = db.query(SystemSettings).first()
        if settings:
            settings.maintenance_mode = not settings.maintenance_mode
            settings.updated_at = datetime.now()
            settings.updated_by = query.from_user.id
            db.commit()
        
        status = "مفعل" if settings.maintenance_mode else "معطل"
        await query.answer(f"✅ تم {status} وضع الصيانة", show_alert=True)
        await admin_system(update, context)
    finally:
        db.close()

async def toggle_transfer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تفعيل/تعطيل تحويل النقاط"""
    query = update.callback_query
    await query.answer()
    db = get_db()
    
    try:
        settings = db.query(SystemSettings).first()
        if settings:
            settings.transfer_enabled = not settings.transfer_enabled
            settings.updated_at = datetime.now()
            settings.updated_by = query.from_user.id
            db.commit()
        
        status = "تفعيل" if settings.transfer_enabled else "تعطيل"
        await query.answer(f"✅ تم {status} تحويل النقاط", show_alert=True)
        await admin_transfer(update, context)
    finally:
        db.close()

async def edit_transfer_fee_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تعديل عمولة التحويل"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "💰 تعديل عمولة التحويل\n\n"
        "ارسل النسبة المئوية الجديدة (من 0 إلى 50):\n"
        "مثال: `5` للعمولة 5%\n\n"
        "⚠️ ملاحظة: العمولة تحسب من المبلغ المحول"
    )
    
    context.user_data['awaiting_transfer_fee'] = True

async def edit_maintenance_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تعديل رسالة الصيانة"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "✏️ تعديل رسالة الصيانة\n\n"
        "ارسل الرسالة الجديدة:\n\n"
        "💡 سيتم عرض هذه الرسالة للمستخدمين عندما يكون البوت تحت الصيانة"
    )
    
    context.user_data['awaiting_maintenance_msg'] = True

async def view_transfers_log(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض سجل التحويلات"""
    query = update.callback_query
    await query.answer()
    db = get_db()
    
    try:
        # جلب آخر 10 تحويلات
        transfers = db.query(PointsTransfer).order_by(desc(PointsTransfer.transfer_date)).limit(10).all()
        
        if not transfers:
            text = "📋 لا توجد تحويلات سابقة."
        else:
            text = "📋 آخر 10 تحويلات:\n\n"
            for transfer in transfers:
                from_user = db.query(User).filter_by(user_id=transfer.from_user_id).first()
                to_user = db.query(User).filter_by(user_id=transfer.to_user_id).first()
                
                from_name = from_user.first_name if from_user else "مجهول"
                to_name = to_user.first_name if to_user else "مجهول"
                
                text += (
                    f"🔄 التحويل #{transfer.id}\n"
                    f"📤 من: {from_name} ({transfer.from_user_id})\n"
                    f"📥 إلى: {to_name} ({transfer.to_user_id})\n"
                    f"💰 المبلغ: {transfer.amount} نقطة\n"
                    f"💸 العمولة: {transfer.fee_amount} نقطة ({transfer.fee_percent}%)\n"
                    f"🕒 الوقت: {transfer.transfer_date.strftime('%Y-%m-%d %H:%M')}\n"
                    f"────────────────────\n"
                )
        
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="admin_transfer")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    finally:
        db.close()

async def handle_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة استدعاءات الإدارة"""
    query = update.callback_query
    await query.answer()
    data = query.data
    
    if data == "admin_stats":
        await admin_stats(update, context)
    elif data == "admin_users":
        await admin_users(update, context)
    elif data.startswith("show_all_users_"):
        await show_all_users(update, context)
    elif data == "admin_admins":
        await admin_admins(update, context)
    elif data == "list_admins":
        await list_admins(update, context)
    elif data == "admin_channels":
        await admin_channels(update, context)
    elif data == "admin_groups":
        await admin_groups(update, context)
    elif data == "admin_requests":
        await admin_requests(update, context)
    elif data == "admin_system":
        await admin_system(update, context)
    elif data == "admin_points":
        await admin_points(update, context)
    elif data == "admin_transfer":
        await admin_transfer(update, context)
    elif data == "admin_broadcast":
        await admin_broadcast(update, context)
    elif data == "toggle_maintenance":
        await toggle_maintenance(update, context)
    elif data == "toggle_transfer":
        await toggle_transfer(update, context)
    elif data == "edit_transfer_fee_menu":
        await edit_transfer_fee_menu(update, context)
    elif data == "edit_maintenance_msg":
        await edit_maintenance_msg(update, context)
    elif data == "view_transfers_log":
        await view_transfers_log(update, context)
    elif data.startswith("approve_request_"):
        await approve_funding_request(update, context)
    elif data.startswith("reject_request_"):
        await reject_funding_request(update, context)

async def approve_funding_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """الموافقة على طلب تمويل"""
    query = update.callback_query
    await query.answer()
    
    try:
        request_id = int(query.data.split("_")[2])
        db = get_db()
        
        request = db.query(FundingRequest).filter_by(id=request_id).first()
        if not request:
            await query.answer("❌ الطلب غير موجود!", show_alert=True)
            return
        
        request.status = 'approved'
        request.approved_by = query.from_user.id
        request.updated_at = datetime.now()
        db.commit()
        
        # إعلام المستخدم
        try:
            user = db.query(User).filter_by(user_id=request.user_id).first()
            if user:
                await context.bot.send_message(
                    user.user_id,
                    f"✅ تمت الموافقة على طلبك #{request_id}\n"
                    f"👥 سيتم البدء بإضافة {request.requested_members} عضو قريباً."
                )
        except:
            pass
        
        await query.answer(f"✅ تمت الموافقة على الطلب #{request_id}", show_alert=True)
        await admin_requests(update, context)
        
    except Exception as e:
        await query.answer(f"❌ خطأ: {str(e)}", show_alert=True)
    finally:
        db.close()

async def reject_funding_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """رفض طلب تمويل"""
    query = update.callback_query
    await query.answer()
    
    try:
        request_id = int(query.data.split("_")[2])
        db = get_db()
        
        request = db.query(FundingRequest).filter_by(id=request_id).first()
        if not request:
            await query.answer("❌ الطلب غير موجود!", show_alert=True)
            return
        
        # استرجاع النقاط للمستخدم
        user = db.query(User).filter_by(user_id=request.user_id).first()
        if user:
            user.points += request.points_cost
        
        request.status = 'rejected'
        request.approved_by = query.from_user.id
        db.commit()
        
        # إعلام المستخدم
        try:
            await context.bot.send_message(
                user.user_id,
                f"❌ تم رفض طلبك #{request_id}\n"
                f"💰 تم إرجاع {request.points_cost} نقطة لحسابك."
            )
        except:
            pass
        
        await query.answer(f"❌ تم رفض الطلب #{request_id}", show_alert=True)
        await admin_requests(update, context)
        
    except Exception as e:
        await query.answer(f"❌ خطأ: {str(e)}", show_alert=True)
    finally:
        db.close()

async def handle_admin_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة مدخلات الإدارة"""
    text = update.message.text.strip()
    user_id = update.effective_user.id
    
    db = get_db()
    try:
        user = db.query(User).filter_by(user_id=user_id).first()
        if not user or not user.is_admin:
            return
        
        # معالجة عمولة التحويل
        if 'awaiting_transfer_fee' in context.user_data:
            try:
                fee_percent = int(text)
                
                if fee_percent < 0 or fee_percent > 50:
                    await update.message.reply_text("❌ النسبة يجب أن تكون بين 0 و 50!")
                    return
                
                settings = db.query(SystemSettings).first()
                if settings:
                    old_fee = settings.transfer_fee_percent
                    settings.transfer_fee_percent = fee_percent
                    settings.updated_at = datetime.now()
                    settings.updated_by = user_id
                    db.commit()
                    
                    await update.message.reply_text(
                        f"✅ تم تغيير عمولة التحويل من {old_fee}% إلى {fee_percent}%"
                    )
                
                del context.user_data['awaiting_transfer_fee']
                
            except ValueError:
                await update.message.reply_text("❌ الرجاء إدخال رقم صحيح!")
        
        # معالجة رسالة الصيانة
        elif 'awaiting_maintenance_msg' in context.user_data:
            new_message = text
            
            if not new_message:
                await update.message.reply_text("❌ الرسالة لا يمكن أن تكون فارغة!")
                return
            
            settings = db.query(SystemSettings).first()
            if settings:
                settings.maintenance_message = new_message
                settings.updated_at = datetime.now()
                settings.updated_by = user_id
                db.commit()
                
                await update.message.reply_text(f"✅ تم تحديث رسالة الصيانة:\n\n{new_message}")
            
            del context.user_data['awaiting_maintenance_msg']
    
    finally:
        db.close()
