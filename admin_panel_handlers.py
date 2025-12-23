herefrom telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import session, User, Channel, GroupSource, PointsSettings, AdminContact
from datetime import datetime

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # إحصائيات عامة
    total_users = session.query(User).count()
    total_admins = session.query(User).filter_by(is_admin=True).count()
    banned_users = session.query(User).filter_by(is_banned=True).count()
    total_points = session.query(User).with_entities(User.points).all()
    total_points_sum = sum([p[0] for p in total_points if p[0]])
    
    # طلبات التمويل
    from sqlalchemy import func
    total_requests = session.query(func.count(FundingRequest.id)).scalar()
    pending_requests = session.query(func.count(FundingRequest.id)).filter_by(status='pending').scalar()
    completed_requests = session.query(func.count(FundingRequest.id)).filter_by(status='completed').scalar()
    
    text = f"""
    📊 إحصائيات النظام:
    
    👥 المستخدمين:
    • إجمالي المستخدمين: {total_users}
    • المشرفين: {total_admins}
    • المحظورين: {banned_users}
    
    ⭐ النقاط:
    • إجمالي النقاط: {total_points_sum}
    
    📋 طلبات التمويل:
    • إجمالي الطلبات: {total_requests}
    • قيد الانتظار: {pending_requests}
    • المكتملة: {completed_requests}
    
    📢 القنوات والمجموعات:
    • القنوات المسجلة: {session.query(Channel).count()}
    • مجموعات المصدر: {session.query(GroupSource).count()}
    """
    
    keyboard = [[InlineKeyboardButton("🔙 رجوع للوحة", callback_data="admin_panel")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def admin_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = """
    👥 إدارة المستخدمين
    
    اختر الإجراء:
    """
    
    keyboard = [
        [InlineKeyboardButton("📋 عرض جميع المستخدمين", callback_data="show_all_users")],
        [InlineKeyboardButton("🔍 بحث عن مستخدم", callback_data="search_user")],
        [InlineKeyboardButton("🚫 حظر مستخدم", callback_data="ban_user_menu")],
        [InlineKeyboardButton("✅ فك حظر مستخدم", callback_data="unban_user_menu")],
        [InlineKeyboardButton("⭐ إضافة نقاط", callback_data="add_points_menu")],
        [InlineKeyboardButton("✉️ إرسال رسالة", callback_data="send_message_menu")],
        [InlineKeyboardButton("🔙 رجوع للوحة", callback_data="admin_panel")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def admin_admins(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        [InlineKeyboardButton("🔧 تعديل صلاحيات", callback_data="edit_permissions")],
        [InlineKeyboardButton("🔙 رجوع للوحة", callback_data="admin_panel")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def admin_channels(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        [InlineKeyboardButton("⚡ تفعيل/تعطيل", callback_data="toggle_groups")],
        [InlineKeyboardButton("🔙 رجوع للوحة", callback_data="admin_panel")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def admin_requests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    from database import FundingRequest
    
    # جلب الطلبات المعلقة
    pending_requests = session.query(FundingRequest).filter_by(status='pending').limit(10).all()
    
    if not pending_requests:
        text = "✅ لا توجد طلبات معلقة حالياً."
    else:
        text = "📋 طلبات التمويل المعلقة:\n\n"
        for req in pending_requests:
            user = session.query(User).filter_by(user_id=req.user_id).first()
            username = user.username if user else "مجهول"
            text += f"• #{req.id} - @{username}\n"
            text += f"  👥 {req.requested_members} عضو | 💰 {req.points_cost} نقطة\n"
            text += f"  🕒 {req.created_at.strftime('%Y-%m-%d %H:%M')}\n\n"
    
    keyboard = [
        [InlineKeyboardButton("🔄 تحديث", callback_data="admin_requests")],
        [InlineKeyboardButton("📊 جميع الطلبات", callback_data="all_requests")],
        [InlineKeyboardButton("🔙 رجوع للوحة", callback_data="admin_panel")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def admin_points(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    settings = session.query(PointsSettings).first()
    if not settings:
        settings = PointsSettings()
        session.add(settings)
        session.commit()
    
    text = f"""
    ⚙️ إعدادات النقاط الحالية:
    
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

async def admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

async def handle_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    
    if data == "admin_stats":
        await admin_stats(update, context)
    elif data == "admin_users":
        await admin_users(update, context)
    elif data == "admin_admins":
        await admin_admins(update, context)
    elif data == "admin_channels":
        await admin_channels(update, context)
    elif data == "admin_groups":
        await admin_groups(update, context)
    elif data == "admin_requests":
        await admin_requests(update, context)
    elif data == "admin_points":
        await admin_points(update, context)
    elif data == "admin_broadcast":
        await admin_broadcast(update, context)
    elif data == "back_to_main":
        await start_command(update, context)
    elif data == "admin_panel":
        await show_admin_panel(query, context)
