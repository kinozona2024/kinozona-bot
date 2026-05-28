import os
import sys
import logging
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, MessageHandler,
    ConversationHandler, ContextTypes, filters
)

from database import db

# .env faylni yuklash
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "0").split(",")))

if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
    print("=" * 60)
    print("XATO: BOT_TOKEN topilmadi!")
    print("Secrets bo'limiga BOT_TOKEN qo'shing.")
    print("=" * 60)
    sys.exit(1)

print("=" * 60)
print(f"TOKEN TOPILDI: {BOT_TOKEN[:20]}...")
print(f"ADMINLAR: {ADMIN_IDS}")
print("=" * 60)

BOT_NAME = "KinoZona"
CATEGORIES = {
    "urush": "Urush",
    "jangari": "Jangari",
    "aksiya": "Aksiya",
    "komediya": "Komediya",
    "romantik": "Romantik",
    "drama": "Drama",
    "boshqa": "Boshqa"
}

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎬 BARCHA KINOLAR", callback_data="all_movies")],
        [InlineKeyboardButton("📁 KATEGORIYALAR", callback_data="categories")],
        [InlineKeyboardButton("⭐ TOP 10", callback_data="top_movies")],
        [InlineKeyboardButton("🆕 YANGILAR", callback_data="new_movies")],
        [InlineKeyboardButton("🔍 QIDIRISH", callback_data="search")],
        [InlineKeyboardButton("ℹ️ BOT HAQIDA", callback_data="about")]
    ])


CATEGORY_EMOJIS = {
    "urush": "⚔️",
    "jangari": "🎖️",
    "aksiya": "💥",
    "komediya": "😂",
    "romantik": "💕",
    "drama": "🎭",
    "boshqa": "📚"
}


def categories_menu():
    keyboard = []
    items = list(CATEGORIES.items())
    for i in range(0, len(items), 2):
        row = []
        for j in range(i, min(i + 2, len(items))):
            key, name = items[j]
            emoji = CATEGORY_EMOJIS.get(key, "🎬")
            row.append(InlineKeyboardButton(f"{emoji} {name}", callback_data=f"cat_{key}"))
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("🚪 ORQAGA", callback_data="back_main")])
    return InlineKeyboardMarkup(keyboard)


def back_button(callback_data="back_main"):
    return InlineKeyboardMarkup([[InlineKeyboardButton("🚪 ORQAGA", callback_data=callback_data)]])


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.add_user(user.id, user.username, user.first_name, user.last_name)

    if db.is_banned(user.id):
        await update.message.reply_text("⛔ Siz bloklangansiz!")
        return

    # Deep link: /start KOD — to'g'ridan-to'g'ri kinoni yuborish
    if context.args:
        code = context.args[0].upper()
        movie = db.get_movie(code=code)

        if movie:
            text = f"""🎬 *{movie['title']}*

🆔 Kod: `{movie['code']}`
🇺🇿 Til: {movie['language']}
🎭 Janr: {movie['genre'] or 'N/A'}
⭐ Reyting: {movie['rating'] or 'N/A'}/10
⏳ Davomiylik: {movie['duration'] or 'N/A'}
💾 Hajm: {movie['size'] or 'N/A'}
🎞️ Sifat: {movie['quality']}

📝 {movie['description'] or 'Tavsif yoq'}"""

            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("📥 YUKLAB OLISH", callback_data=f"download_{movie['id']}")],
                [InlineKeyboardButton("🏠 ASOSIY MENYU", callback_data="back_main")]
            ])
            await update.message.reply_text(text, reply_markup=keyboard, parse_mode="Markdown")
            return
        else:
            await update.message.reply_text(
                f"❌ *{code}* kodli film topilmadi!\n\nQuyidagilardan birini tanlang:",
                reply_markup=main_menu(),
                parse_mode="Markdown"
            )
            return

    welcome = f"""🎬 *Assalomu alaykum, {user.first_name}!*

*{BOT_NAME}* ga xush kelibsiz!

📥 Eng sara tarjima kinolar
⭐ TOP filmlar
🔍 Qidirish funksiyasi
🇺🇿 Barchasi O'zbek tilida

👇 Tanlang:"""

    await update.message.reply_text(welcome, reply_markup=main_menu(), parse_mode="Markdown")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot_info = await context.bot.get_me()
    username = bot_info.username
    text = f"""🤖 *Yordam*

/start — 🚀 Botni ishga tushirish
/q nom — 🔍 Film qidirish
/admin — 🔧 Admin panel (faqat adminlar)

💡 *Do'stlarga kino ulashish:*
Kino sahifasidagi `Kod` ni olib quyidagi havolani yuboring:

`https://t.me/{username}?start=KOD`

Masalan: `https://t.me/{username}?start=MOV001`

Havola bosilganda do'stingiz to'g'ridan-to'g'ri o'sha kinoga o'tadi!"""
    await update.message.reply_text(text, parse_mode="Markdown")


async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("🔍 Film nomini kiriting:\nMisol: /q Platoon")
        return

    query = " ".join(context.args)
    movies = db.search_movies(query)

    if not movies:
        await update.message.reply_text("❌ Film topilmadi!", reply_markup=main_menu())
        return

    keyboard = []
    for movie in movies[:10]:
        keyboard.append([InlineKeyboardButton(
            f"🎬 {movie['title']} ({movie['year'] or 'N/A'})",
            callback_data=f"movie_{movie['id']}"
        )])
    keyboard.append([InlineKeyboardButton("🚪 ORQAGA", callback_data="back_main")])

    await update.message.reply_text(
        f"🔍 *{len(movies)} ta natija:*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


def admin_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ KINO QO'SHISH", callback_data="admin_add")],
        [InlineKeyboardButton("📊 STATISTIKA", callback_data="admin_stats"),
         InlineKeyboardButton("📋 KINOLAR", callback_data="admin_list")],
        [InlineKeyboardButton("🗑️ O'CHIRISH", callback_data="admin_delete"),
         InlineKeyboardButton("📢 BROADCAST", callback_data="admin_broadcast")],
        [InlineKeyboardButton("👥 FOYDALANUVCHILAR", callback_data="admin_users")],
        [InlineKeyboardButton("❓ YORDAM", callback_data="admin_help")],
        [InlineKeyboardButton("🏠 ASOSIY MENYU", callback_data="back_main")]
    ])


async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Siz admin emassiz!")
        return

    stats = db.get_stats()
    text = f"""🔧 *ADMIN PANEL*

📊 Statistika:
🎬 Kinolar: {stats['total_movies']}
👥 Foydalanuvchilar: {stats['total_users']}"""

    await update.message.reply_text(text, reply_markup=admin_keyboard(), parse_mode="Markdown")


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    if data == "admin":
        if user_id not in ADMIN_IDS:
            await query.answer("⛔ Siz admin emassiz!", show_alert=True)
            return
        stats = db.get_stats()
        text = f"""🔧 *ADMIN PANEL*

📊 Statistika:
🎬 Kinolar: {stats['total_movies']}
👥 Foydalanuvchilar: {stats['total_users']}"""
        await query.edit_message_text(text, reply_markup=admin_keyboard(), parse_mode="Markdown")
        return

    if data == "admin_users":
        if user_id not in ADMIN_IDS:
            return
        users = db.get_all_users()
        all_users = db.conn.execute("SELECT * FROM users ORDER BY joined_at DESC LIMIT 20").fetchall()
        all_users = [dict(u) for u in all_users]
        if not all_users:
            await query.edit_message_text("❌ Foydalanuvchilar yo'q!", reply_markup=back_button("admin"))
            return
        keyboard = []
        for u in all_users:
            banned = u.get("is_banned", 0)
            name = u.get("first_name") or u.get("username") or str(u["id"])
            status = "🔴" if banned else "🟢"
            action = f"unban_{u['id']}" if banned else f"ban_{u['id']}"
            btn_text = f"{status} {name} {'(BAN)' if banned else ''}"
            keyboard.append([InlineKeyboardButton(btn_text, callback_data=action)])
        keyboard.append([InlineKeyboardButton("🚪 ORQAGA", callback_data="admin")])
        total = len(all_users)
        banned_count = sum(1 for u in all_users if u.get("is_banned"))
        await query.edit_message_text(
            f"👥 *FOYDALANUVCHILAR* ({total} ta)\n🟢 Faol: {total - banned_count} | 🔴 Banned: {banned_count}\n\nFoydalanuvchiga bosib ban/unban qiling:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        return

    if data.startswith("ban_"):
        if user_id not in ADMIN_IDS:
            return
        target_id = int(data.replace("ban_", ""))
        if target_id in ADMIN_IDS:
            await query.answer("⛔ Adminni ban qilib bo'lmaydi!", show_alert=True)
            return
        db.ban_user(target_id)
        try:
            await context.bot.send_message(
                chat_id=target_id,
                text="⛔ Siz admin tomonidan bloklangansiz."
            )
        except Exception:
            pass
        await query.answer("✅ Foydalanuvchi bloklandi!", show_alert=True)
        # Ro'yxatni yangilash
        all_users = db.conn.execute("SELECT * FROM users ORDER BY joined_at DESC LIMIT 20").fetchall()
        all_users = [dict(u) for u in all_users]
        keyboard = []
        for u in all_users:
            banned = u.get("is_banned", 0)
            name = u.get("first_name") or u.get("username") or str(u["id"])
            status = "🔴" if banned else "🟢"
            action = f"unban_{u['id']}" if banned else f"ban_{u['id']}"
            btn_text = f"{status} {name} {'(BAN)' if banned else ''}"
            keyboard.append([InlineKeyboardButton(btn_text, callback_data=action)])
        keyboard.append([InlineKeyboardButton("🚪 ORQAGA", callback_data="admin")])
        total = len(all_users)
        banned_count = sum(1 for u in all_users if u.get("is_banned"))
        await query.edit_message_text(
            f"👥 *FOYDALANUVCHILAR* ({total} ta)\n🟢 Faol: {total - banned_count} | 🔴 Banned: {banned_count}\n\nFoydalanuvchiga bosib ban/unban qiling:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        return

    if data.startswith("unban_"):
        if user_id not in ADMIN_IDS:
            return
        target_id = int(data.replace("unban_", ""))
        db.unban_user(target_id)
        try:
            await context.bot.send_message(
                chat_id=target_id,
                text="✅ Sizning blokingiz olib tashlandi! Botdan foydalanishingiz mumkin."
            )
        except Exception:
            pass
        await query.answer("✅ Foydalanuvchi blokdan chiqarildi!", show_alert=True)
        all_users = db.conn.execute("SELECT * FROM users ORDER BY joined_at DESC LIMIT 20").fetchall()
        all_users = [dict(u) for u in all_users]
        keyboard = []
        for u in all_users:
            banned = u.get("is_banned", 0)
            name = u.get("first_name") or u.get("username") or str(u["id"])
            status = "🔴" if banned else "🟢"
            action = f"unban_{u['id']}" if banned else f"ban_{u['id']}"
            btn_text = f"{status} {name} {'(BAN)' if banned else ''}"
            keyboard.append([InlineKeyboardButton(btn_text, callback_data=action)])
        keyboard.append([InlineKeyboardButton("🚪 ORQAGA", callback_data="admin")])
        total = len(all_users)
        banned_count = sum(1 for u in all_users if u.get("is_banned"))
        await query.edit_message_text(
            f"👥 *FOYDALANUVCHILAR* ({total} ta)\n🟢 Faol: {total - banned_count} | 🔴 Banned: {banned_count}\n\nFoydalanuvchiga bosib ban/unban qiling:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        return

    if data == "admin_help":
        if user_id not in ADMIN_IDS:
            return
        text = """❓ *ADMIN YORDAM — QO'LLANMA*

━━━━━━━━━━━━━━━━━━━━
➕ *KINO QO'SHISH*
━━━━━━━━━━━━━━━━━━━━
Admin paneldan "➕ KINO QO'SHISH" ni bosing.
Quyidagi ma'lumotlarni ketma-ket kiriting:

🆔 *Kod* — Noyob ID \(masalan: MOV001\)
📝 *Nom* — Film nomi
📁 *Fayl* — Video yoki hujjat yuborish
📅 *Yil* — Chiqish yili
🎭 *Janr* — Janr turi
⭐ *Reyting* — 0 dan 10 gacha
⏳ *Davomiylik* — Masalan: 120 min
💾 *Hajm* — Masalan: 2\.1 GB
📝 *Tavsif* — Qisqacha ma'lumot
📁 *Kategoriya* — Menyudan tanlang

💡 Ma'lumotni o'tkazib yuborish uchun /skip yozing

━━━━━━━━━━━━━━━━━━━━
🗑️ *KINO O'CHIRISH*
━━━━━━━━━━━━━━━━━━━━
"🗑️ O'CHIRISH" ni bosing va ro'yxatdan
o'chirmoqchi bo'lgan kinoni tanlang\.

━━━━━━━━━━━━━━━━━━━━
📢 *BROADCAST \(XABAR YUBORISH\)*
━━━━━━━━━━━━━━━━━━━━
"📢 BROADCAST" ni bosib xabar yozing\.
Xabar barcha foydalanuvchilarga yuboriladi\.
Bekor qilish uchun /cancel yozing\.

━━━━━━━━━━━━━━━━━━━━
🔗 *KINO HAVOLASI ULASHISH*
━━━━━━━━━━━━━━━━━━━━
Kino kodini olib havola tuzing:
`https://t\.me/BOTUSERNAME?start=KOD`
Masalan: `https://t\.me/botim?start=MOV001`

━━━━━━━━━━━━━━━━━━━━
📋 *ADMIN KOMANDALAR*
━━━━━━━━━━━━━━━━━━━━
/admin — Admin panelni ochish
/cancel — Jarayonni bekor qilish
/q nom — Film qidirish"""

        await query.edit_message_text(
            text,
            reply_markup=back_button("admin"),
            parse_mode="MarkdownV2"
        )
        return

    if data == "admin_stats":
        if user_id not in ADMIN_IDS:
            return
        stats = db.get_stats()
        text = f"""📊 *STATISTIKA*

🎬 Kinolar: {stats['total_movies']} ta
👥 Foydalanuvchilar: {stats['total_users']} ta"""
        await query.edit_message_text(text, reply_markup=back_button("admin"), parse_mode="Markdown")
        return

    if data == "admin_list":
        if user_id not in ADMIN_IDS:
            return
        movies = db.get_all_movies()
        if not movies:
            await query.edit_message_text("❌ Kinolar yo'q!", reply_markup=back_button("admin"))
            return
        keyboard = []
        for movie in movies[:20]:
            keyboard.append([InlineKeyboardButton(
                f"🎬 {movie['title']} [{movie['code']}]",
                callback_data=f"movie_{movie['id']}"
            )])
        keyboard.append([InlineKeyboardButton("🚪 ORQAGA", callback_data="admin")])
        await query.edit_message_text(
            f"📋 *KINOLAR RO'YXATI* ({len(movies)} ta)",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        return

    if data == "admin_delete":
        if user_id not in ADMIN_IDS:
            return
        movies = db.get_all_movies()
        if not movies:
            await query.edit_message_text("❌ Kinolar yo'q!", reply_markup=back_button("admin"))
            return
        keyboard = []
        for movie in movies[:20]:
            keyboard.append([InlineKeyboardButton(
                f"🗑️ {movie['title']}",
                callback_data=f"del_{movie['id']}"
            )])
        keyboard.append([InlineKeyboardButton("🚪 ORQAGA", callback_data="admin")])
        await query.edit_message_text(
            "🗑️ O'chirmoqchi bo'lgan kinoni tanlang:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    if data.startswith("del_"):
        if user_id not in ADMIN_IDS:
            return
        movie_id = int(data.replace("del_", ""))
        movie = db.get_movie(movie_id=movie_id)
        if movie and db.delete_movie(movie_id):
            await query.edit_message_text(
                f"✅ *{movie['title']}* o'chirildi!",
                reply_markup=back_button("admin"),
                parse_mode="Markdown"
            )
        else:
            await query.edit_message_text("❌ Xatolik!", reply_markup=back_button("admin"))
        return

    if data == "admin_broadcast":
        if user_id not in ADMIN_IDS:
            return
        await query.edit_message_text(
            "📢 Barcha foydalanuvchilarga yuboriladigan xabarni yozing:\n\n/cancel — bekor qilish",
            reply_markup=back_button("admin")
        )
        return

    if data == "back_main":
        await query.edit_message_text("🏠 Asosiy menyu:", reply_markup=main_menu())
        return

    if data == "all_movies":
        movies = db.get_all_movies()
        if not movies:
            await query.edit_message_text("❌ Kinolar yo'q!", reply_markup=main_menu())
            return
        keyboard = []
        for movie in movies:
            keyboard.append([InlineKeyboardButton(
                f"🎬 {movie['title']} ({movie['year'] or 'N/A'})",
                callback_data=f"movie_{movie['id']}"
            )])
        keyboard.append([InlineKeyboardButton("🚪 ORQAGA", callback_data="back_main")])
        await query.edit_message_text(
            f"🎬 *BARCHA KINOLAR* ({len(movies)} ta)",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        return

    if data == "categories":
        await query.edit_message_text(
            "📁 *KATEGORIYALAR*",
            reply_markup=categories_menu(),
            parse_mode="Markdown"
        )
        return

    if data.startswith("cat_"):
        category = data.replace("cat_", "")
        movies = db.get_all_movies(category=category)
        if not movies:
            await query.answer("❌ Bu kategoriyada film yo'q!", show_alert=True)
            return
        emoji = CATEGORY_EMOJIS.get(category, "🎬")
        keyboard = []
        for movie in movies:
            keyboard.append([InlineKeyboardButton(
                f"🎬 {movie['title']}",
                callback_data=f"movie_{movie['id']}"
            )])
        keyboard.append([InlineKeyboardButton("🚪 ORQAGA", callback_data="categories")])
        await query.edit_message_text(
            f"{emoji} *{CATEGORIES.get(category, category)}* ({len(movies)} ta)",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        return

    if data == "top_movies":
        movies = db.get_all_movies()
        movies.sort(key=lambda x: x.get('rating') or 0, reverse=True)
        top = movies[:10]
        text = "⭐ *TOP 10 FILMLAR*\n\n"
        keyboard = []
        for i, movie in enumerate(top, 1):
            text += f"{i}. 🎬 *{movie['title']}* — ⭐ {movie['rating'] or 'N/A'}/10\n"
            keyboard.append([InlineKeyboardButton(
                f"{i}. 🎬 {movie['title']}",
                callback_data=f"movie_{movie['id']}"
            )])
        keyboard.append([InlineKeyboardButton("🚪 ORQAGA", callback_data="back_main")])
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return

    if data == "new_movies":
        movies = db.get_all_movies()[:5]
        keyboard = []
        for movie in movies:
            keyboard.append([InlineKeyboardButton(
                f"🆕 {movie['title']} ({movie['year'] or 'N/A'})",
                callback_data=f"movie_{movie['id']}"
            )])
        keyboard.append([InlineKeyboardButton("🚪 ORQAGA", callback_data="back_main")])
        await query.edit_message_text(
            "🆕 *YANGI QO'SHILGANLAR*",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        return

    if data == "search":
        await query.edit_message_text(
            "🔍 Film nomini yozing:\nMisol: /q Platoon",
            reply_markup=back_button()
        )
        return

    if data.startswith("movie_"):
        movie_id = int(data.replace("movie_", ""))
        movie = db.get_movie(movie_id=movie_id)
        if not movie:
            await query.answer("❌ Film topilmadi!", show_alert=True)
            return
        text = f"""🎬 *{movie['title']}*

🆔 Kod: `{movie['code']}`
🇺🇿 Til: {movie['language']}
🎭 Janr: {movie['genre'] or 'N/A'}
⭐ Reyting: {movie['rating'] or 'N/A'}/10
⏳ Davomiylik: {movie['duration'] or 'N/A'}
💾 Hajm: {movie['size'] or 'N/A'}
🎞️ Sifat: {movie['quality']}

📝 {movie['description'] or 'Tavsif yoq'}"""

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📥 YUKLAB OLISH", callback_data=f"download_{movie['id']}")],
            [InlineKeyboardButton("🚪 ORQAGA", callback_data="all_movies")]
        ])
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")
        return

    if data.startswith("download_"):
        movie_id = int(data.replace("download_", ""))
        movie = db.get_movie(movie_id=movie_id)
        if not movie:
            await query.answer("❌ Film topilmadi!", show_alert=True)
            return
        if not movie.get('file_id'):
            await query.answer("❌ Fayl yo'q!", show_alert=True)
            return
        await query.answer("📤 Yuborilmoqda...")
        try:
            await query.message.reply_video(
                video=movie['file_id'],
                caption=f"✅ *{movie['title']}*\n\n🎞️ Sifat: {movie['quality']}",
                parse_mode="Markdown"
            )
            await query.message.reply_text(
                "✅ Film yuborildi! Boshqa tanlaysizmi?",
                reply_markup=main_menu()
            )
        except Exception as e:
            logger.error(f"Download error: {e}")
            await query.message.reply_text("❌ Xatolik yuz berdi!")
        return

    if data == "about":
        stats = db.get_stats()
        text = f"""ℹ️ *{BOT_NAME}*

📥 Eng sara tarjima kinolar
⭐ TOP filmlar
🔍 Qidirish funksiyasi
🇺🇿 Barchasi O'zbek tilida

📊 Statistika:
🎬 Kinolar: {stats['total_movies']} ta
👥 Foydalanuvchilar: {stats['total_users']} ta

🤖 Bot versiya: 1.0"""
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🚪 ORQAGA", callback_data="back_main")]
        ])
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")
        return


# ========== ADMIN KINO QO'SHISH ==========
(ADD_CODE, ADD_TITLE, ADD_FILE, ADD_YEAR, ADD_GENRE, ADD_RATING,
 ADD_DURATION, ADD_SIZE, ADD_DESC, ADD_CATEGORY) = range(10)
BROADCAST = 10


async def admin_add_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "➕ *Kino qo'shish*\n\n"
        "🆔 Kino kodini kiriting:\n"
        "_(masalan: MOV001, ACTION01)_",
        parse_mode="Markdown"
    )
    return ADD_CODE


async def add_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    code = update.message.text.strip().upper()
    if db.get_movie(code=code):
        await update.message.reply_text("❌ Bu kod allaqachon bor! Boshqa kod kiriting:")
        return ADD_CODE
    context.user_data['new_movie'] = {'code': code}
    await update.message.reply_text("📝 Kino nomini kiriting:")
    return ADD_TITLE


async def add_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['new_movie']['title'] = update.message.text
    await update.message.reply_text(
        "📁 Kino faylini yuboring:\n_(Video yoki hujjat sifatida)_",
        parse_mode="Markdown"
    )
    return ADD_FILE


async def add_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.video:
        file_id = update.message.video.file_id
        video = update.message.video
        if video.duration:
            mins = video.duration // 60
            secs = video.duration % 60
            context.user_data['new_movie']['duration'] = f"{mins}:{secs:02d} min"
        if video.file_size:
            size_mb = video.file_size / (1024 * 1024)
            if size_mb >= 1024:
                context.user_data['new_movie']['size'] = f"{size_mb / 1024:.1f} GB"
            else:
                context.user_data['new_movie']['size'] = f"{size_mb:.0f} MB"
    elif update.message.document:
        file_id = update.message.document.file_id
        doc = update.message.document
        if doc.file_size:
            size_mb = doc.file_size / (1024 * 1024)
            if size_mb >= 1024:
                context.user_data['new_movie']['size'] = f"{size_mb / 1024:.1f} GB"
            else:
                context.user_data['new_movie']['size'] = f"{size_mb:.0f} MB"
    else:
        await update.message.reply_text("❌ Video yoki fayl yuboring!")
        return ADD_FILE

    context.user_data['new_movie']['file_id'] = file_id

    # Caption (fayl ustidagi matn) → avtomatik tavsif
    if update.message.caption:
        context.user_data['new_movie']['description'] = update.message.caption

    caption_note = ""
    if update.message.caption:
        caption_note = f"\n📝 Tavsif saqlandi: _{update.message.caption[:50]}_"

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⚔️ Urush", callback_data="newcat_urush"),
         InlineKeyboardButton("🎖️ Jangari", callback_data="newcat_jangari")],
        [InlineKeyboardButton("💥 Aksiya", callback_data="newcat_aksiya"),
         InlineKeyboardButton("😂 Komediya", callback_data="newcat_komediya")],
        [InlineKeyboardButton("💕 Romantik", callback_data="newcat_romantik"),
         InlineKeyboardButton("🎭 Drama", callback_data="newcat_drama")],
        [InlineKeyboardButton("📚 Boshqa", callback_data="newcat_boshqa")]
    ])
    await update.message.reply_text(
        f"✅ Fayl qabul qilindi!{caption_note}\n\n📁 Kategoriyani tanlang:",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    return ADD_CATEGORY


async def add_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    category = query.data.replace("newcat_", "")
    context.user_data['new_movie']['category'] = category
    context.user_data['new_movie']['added_by'] = query.from_user.id
    movie = context.user_data['new_movie']
    success = db.add_movie(**movie)
    emoji = CATEGORY_EMOJIS.get(category, "🎬")
    if success:
        await query.edit_message_text(
            f"✅ *Kino qo'shildi!*\n\n🎬 {movie['title']}\n🆔 Kod: {movie['code']}\n{emoji} Kategoriya: {category}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔧 Admin panel", callback_data="admin")]
            ]),
            parse_mode="Markdown"
        )
    else:
        await query.edit_message_text("❌ Xatolik!", reply_markup=back_button("admin"))
    return ConversationHandler.END


async def broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return ConversationHandler.END

    text = update.message.text
    users = db.get_all_users()
    sent = 0
    failed = 0

    for user in users:
        try:
            await context.bot.send_message(chat_id=user['id'], text=text)
            sent += 1
        except Exception:
            failed += 1

    await update.message.reply_text(
        f"✅ Xabar yuborildi!\n📤 Yuborildi: {sent}\n❌ Xato: {failed}",
        reply_markup=back_button("admin")
    )
    return ConversationHandler.END


async def broadcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.from_user.id not in ADMIN_IDS:
        return ConversationHandler.END
    await query.edit_message_text(
        "📢 Barcha foydalanuvchilarga yuboriladigan xabarni yozing:\n\n/cancel — bekor qilish"
    )
    return BROADCAST


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ Bekor qilindi!", reply_markup=main_menu())
    return ConversationHandler.END


async def post_init(application: Application):
    commands = [
        BotCommand("start", "Botni ishga tushirish"),
        BotCommand("q", "Film qidirish"),
        BotCommand("admin", "Admin panel"),
        BotCommand("help", "Yordam"),
    ]
    await application.bot.set_my_commands(commands)


def main():
    application = Application.builder().token(BOT_TOKEN).post_init(post_init).build()

    add_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_add_start, pattern="^admin_add$")],
        states={
            ADD_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_code)],
            ADD_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_title)],
            ADD_FILE: [MessageHandler(filters.VIDEO | filters.Document.ALL, add_file)],
            ADD_CATEGORY: [CallbackQueryHandler(add_category, pattern="^newcat_")],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_message=False
    )

    broadcast_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(broadcast_start, pattern="^admin_broadcast$")],
        states={
            BROADCAST: [MessageHandler(filters.TEXT & ~filters.COMMAND, broadcast_message)]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_message=False
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("q", search_command))
    application.add_handler(CommandHandler("admin", admin_panel))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(add_conv)
    application.add_handler(broadcast_conv)
    application.add_handler(CallbackQueryHandler(handle_callback))

    print(f"\n{BOT_NAME} ishga tushmoqda...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
