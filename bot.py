import os
import asyncio
import logging
import urllib.request
import urllib.parse
import json
import math
from datetime import datetime, timedelta, timezone
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ContextTypes
)
from telegram.error import BadRequest, Forbidden
from flask import Flask, jsonify
from supabase import create_client, Client

# 📝 LOGGING
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# 🔐 ENV VARIABLES
TOKEN = os.getenv("BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
CRON_SECRET = os.getenv("CRON_SECRET", "default_secret_change_me")

# 🗄️ SUPABASE CLIENT
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None

# 🌍 TIMEZONE - Tashkent (UTC+5)
TZ = timezone(timedelta(hours=5))

# 🕌 NAMOZ NOMLARI
PRAYER_NAMES = {
    "Fajr": "Bomdod",
    "Dhuhr": "Peshin",
    "Asr": "Asr",
    "Maghrib": "Shom",
    "Isha": "Xufton"
}
PRAYER_ORDER = ["Fajr", "Dhuhr", "Asr", "Maghrib", "Isha"]

# 🏙️ O'ZBEKISTON SHAHARLARI
CITIES = {
    "Toshkent": {"lat": 41.2995, "lon": 69.2401},
    "Namangan": {"lat": 40.9983, "lon": 71.6726},
    "Andijon": {"lat": 40.7821, "lon": 72.3442},
    "Farg'ona": {"lat": 40.3893, "lon": 71.7878},
    "Samarqand": {"lat": 39.6542, "lon": 66.9597},
    "Buxoro": {"lat": 39.7681, "lon": 64.4556},
    "Qashqadaryo": {"lat": 38.8587, "lon": 65.7894},
    "Surxondaryo": {"lat": 37.2244, "lon": 67.2783},
    "Jizzax": {"lat": 40.1158, "lon": 67.8422},
    "Sirdaryo": {"lat": 40.8400, "lon": 68.6608},
    "Navoiy": {"lat": 40.0844, "lon": 65.3792},
    "Xorazm": {"lat": 41.5500, "lon": 60.6314},
    "Qoraqalpog'iston": {"lat": 42.4651, "lon": 59.6166},
}

# 📖 KUNLIK HADISLAR (oddiy ro'yxat)
HADITHS = [
    "Rasululloh ﷺ aytdilar: «Eng yaxshilaringiz odamlarga foyda keltiruvchidir.» (Tabaroniy)",
    "Rasululloh ﷺ aytdilar: «Mo'min mo'minga ko'zguga o'xshaydi.» (Abu Dovud)",
    "Rasululloh ﷺ aytdilar: «Hech biringiz, o'ziga sevganini birodariga sevmaguncha, mo'min bo'lmaydi.» (Buxoriy)",
    "Rasululloh ﷺ aytdilar: «Tabassumingiz birodaringizga sadaqa.» (Termiziy)",
    "Rasululloh ﷺ aytdilar: «Allohga eng sevimli amal — vaqtida o'qilgan namozdir.» (Buxoriy)",
    "Rasululloh ﷺ aytdilar: «Kim bir kun ramazonda ro'za tutsa, Alloh uning yuzini do'zaxdan 70 yil olib qo'yadi.» (Buxoriy, Muslim)",
    "Rasululloh ﷺ aytdilar: «Ilm izlash har bir musulmonga farzdir.» (Ibn Moja)",
    "Rasululloh ﷺ aytdilar: «Insonlarga rahmqilmagan kishiga Alloh rahm qilmaydi.» (Buxoriy)",
    "Rasululloh ﷺ aytdilar: «Eng yaxshi sadaqa — odamlar orasida tinchlik o'rnatishdir.» (Abu Dovud)",
    "Rasululloh ﷺ aytdilar: «Ota-ona roziligi — Alloh roziligi.» (Termiziy)",
    "Rasululloh ﷺ aytdilar: «Haqiqiy kuchli kishi g'azabini jilovlay oladigan kishidir.» (Buxoriy)",
    "Rasululloh ﷺ aytdilar: «Ko'p kulmang, chunki ko'p kulish qalbni o'ldiradi.» (Termiziy)",
    "Rasululloh ﷺ aytdilar: «Kim Allohga va oxirat kuniga ishonsa, yo yaxshi gapirsin yoki sukut qilsin.» (Buxoriy)",
    "Rasululloh ﷺ aytdilar: «Qo'shni huquqi shu darajada muhimki, men uni vorisga aylantiradi deb o'ylagandim.» (Buxoriy)",
    "Rasululloh ﷺ aytdilar: «Pokligingiz — imoningizning yarmi.» (Muslim)",
    "Rasululloh ﷺ aytdilar: «Erta turing, baraka erta turishdadir.» (Termiziy)",
    "Rasululloh ﷺ aytdilar: «Allohni eslash qalbni tirik qiladi.» (Buxoriy)",
    "Rasululloh ﷺ aytdilar: «Sabr — yorug'likdir.» (Muslim)",
    "Rasululloh ﷺ aytdilar: «Hech bir musulmon birodariga 3 kundan ortiq qarama-qarshi turmasin.» (Buxoriy)",
    "Rasululloh ﷺ aytdilar: «Eng baxtli kishi — Allohni tanigan kishidir.» (Tabaroniy)",
    "Rasululloh ﷺ aytdilar: «Avvalo o'zingizni tarbiyalang, keyin oilangizni.» (Buxoriy)",
    "Rasululloh ﷺ aytdilar: «Yomon so'z aytadigandan ko'ra sukut afzaldir.» (Termiziy)",
    "Rasululloh ﷺ aytdilar: «Insof — imondandir.» (Buxoriy)",
    "Rasululloh ﷺ aytdilar: «Mehnat — ibodatning yarmi.» (Tabaroniy)",
    "Rasululloh ﷺ aytdilar: «Tongdagi ikki rakat namoz dunyo va undagi narsalardan yaxshiroq.» (Muslim)",
    "Rasululloh ﷺ aytdilar: «Janoza ortidan yurish — savobdir.» (Buxoriy)",
    "Rasululloh ﷺ aytdilar: «Salomni keng tarqating.» (Muslim)",
    "Rasululloh ﷺ aytdilar: «Zikrning eng yaxshisi — La ilaha illallohdir.» (Termiziy)",
    "Rasululloh ﷺ aytdilar: «Yaxshilik qilingki, sizga ham yaxshilik qiladi.» (Tabaroniy)",
    "Rasululloh ﷺ aytdilar: «Allohga tavakkul qilgan kishi muvaffaq bo'ladi.» (Termiziy)",
]

# =========================
# 🌐 NAMOZ VAQTLARI API
# =========================
def get_prayer_times(city, date_str=None):
    """Aladhan API'dan namoz vaqtlarini olish."""
    if city not in CITIES:
        return None
    coords = CITIES[city]
    if date_str is None:
        date_str = datetime.now(TZ).strftime("%d-%m-%Y")
    url = (
        f"https://api.aladhan.com/v1/timings/{date_str}"
        f"?latitude={coords['lat']}&longitude={coords['lon']}"
        f"&method=2&school=1"
    )
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            data = json.loads(r.read().decode())
            if data.get("code") == 200:
                return data["data"]
    except Exception as e:
        logging.error(f"API xato: {e}")
    return None

def get_qibla(city):
    """Qibla yo'nalishini Aladhan API'dan olish."""
    if city not in CITIES:
        return None
    coords = CITIES[city]
    url = f"https://api.aladhan.com/v1/qibla/{coords['lat']}/{coords['lon']}"
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            data = json.loads(r.read().decode())
            if data.get("code") == 200:
                return data["data"]["direction"]
    except Exception as e:
        logging.error(f"Qibla xato: {e}")
    return None

# =========================
# 🗄️ DATABASE FUNKSIYALARI
# =========================
def db_get_user(chat_id):
    try:
        r = supabase.table("users").select("*").eq("chat_id", chat_id).execute()
        return r.data[0] if r.data else None
    except Exception as e:
        logging.error(f"DB get_user xato: {e}")
        return None

def db_create_or_update_user(chat_id, **fields):
    try:
        existing = db_get_user(chat_id)
        if existing:
            r = supabase.table("users").update(fields).eq("chat_id", chat_id).execute()
        else:
            data = {"chat_id": chat_id, **fields}
            if "city" not in data:
                data["city"] = "Toshkent"
            r = supabase.table("users").insert(data).execute()
        return r.data[0] if r.data else None
    except Exception as e:
        logging.error(f"DB upsert xato: {e}")
        return None

def db_get_all_agreed_users():
    try:
        r = supabase.table("users").select("*").eq("agreed", True).execute()
        return r.data
    except Exception as e:
        logging.error(f"DB get_all xato: {e}")
        return []

# =========================
# 🤖 BOT HANDLERLAR
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.from_user.id
    user = db_get_user(chat_id)

    if user and user.get("agreed") and user.get("city"):
        # Avvaldan ro'yxatdan o'tgan
        await show_main_menu(update, context, user)
        return

    # Yangi foydalanuvchi - shartlarni ko'rsatish
    text = (
        "🕌 *Assalomu alaykum!*\n\n"
        "*Namoz Vaqtlari Boti*ga xush kelibsiz!\n\n"
        "📌 *Bot quyidagilarni qiladi:*\n"
        "• Har kuni 03:00 da bugungi 5 vaqt namoz vaqtini yuboradi\n"
        "• Har namoz vaqtida sizga eslatma yuboradi\n"
        "• Keyingi namozdan oldin: \"O'qidingizmi?\" deb so'raydi\n"
        "• Statistikangizni saqlaydi\n\n"
        "📜 *Shartlar:*\n"
        "1. Bot sizga kunlik xabarlar yuboradi\n"
        "2. Sizning ma'lumotlaringiz xavfsiz saqlanadi\n"
        "3. Istalgan vaqtda /stop bosib to'xtatish mumkin\n\n"
        "*Davom etishni xohlaysizmi?*"
    )
    keyboard = [
        [InlineKeyboardButton("✅ Roziman, davom etamiz", callback_data="agree_yes")],
        [InlineKeyboardButton("❌ Yo'q, rahmat", callback_data="agree_no")]
    ]
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def agreement_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except BadRequest:
        return

    chat_id = query.from_user.id

    if query.data == "agree_no":
        await query.edit_message_text(
            "Tushundim. Agar fikringiz o'zgarsa, /start yuboring."
        )
        return

    # Roziman -> shahar tanlashga
    db_create_or_update_user(chat_id, agreed=True, city="Toshkent")

    await query.edit_message_text(
        "✅ *Rahmat!*\n\nEndi shahringizni tanlang:",
        parse_mode="Markdown"
    )
    await show_city_selection(update, context)

async def show_city_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = []
    cities = list(CITIES.keys())
    for i in range(0, len(cities), 2):
        row = [InlineKeyboardButton(f"📍 {cities[i]}", callback_data=f"city_{cities[i]}")]
        if i + 1 < len(cities):
            row.append(InlineKeyboardButton(f"📍 {cities[i+1]}", callback_data=f"city_{cities[i+1]}"))
        keyboard.append(row)

    if update.callback_query:
        await update.callback_query.message.reply_text(
            "🏙️ *Shahringizni tanlang:*",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            "🏙️ *Shahringizni tanlang:*",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

async def city_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except BadRequest:
        return

    chat_id = query.from_user.id
    city = query.data.replace("city_", "")

    if city not in CITIES:
        await query.edit_message_text("❌ Shahar topilmadi.")
        return

    db_create_or_update_user(chat_id, city=city, agreed=True)
    user = db_get_user(chat_id)

    await query.edit_message_text(
        f"✅ Shahar tanlandi: *{city}*\n\n"
        f"Endi har kuni namoz vaqtlarini yuboramiz inshaAlloh.",
        parse_mode="Markdown"
    )

    # Asosiy menyu ko'rsatish
    await show_main_menu_message(query.message, user)

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, user):
    await show_main_menu_message(update.message, user)

async def show_main_menu_message(message, user):
    keyboard = [
        [KeyboardButton("🕌 Bugungi namoz vaqtlari")],
        [KeyboardButton("📊 Mening statistikam"), KeyboardButton("🧭 Qibla")],
        [KeyboardButton("📖 Bugungi hadis"), KeyboardButton("⚙️ Sozlamalar")]
    ]
    text = (
        f"🕌 *Assalomu alaykum!*\n\n"
        f"📍 Shaharingiz: *{user.get('city', 'Toshkent')}*\n\n"
        f"Quyidagi menudan tanlang:"
    )
    await message.reply_text(
        text,
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
        parse_mode="Markdown"
    )

async def show_prayer_times(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.from_user.id
    user = db_get_user(chat_id)
    if not user:
        await update.message.reply_text("Iltimos, /start yuboring.")
        return

    city = user["city"]
    today_data = get_prayer_times(city)
    tomorrow_date = (datetime.now(TZ) + timedelta(days=1)).strftime("%d-%m-%Y")
    tomorrow_data = get_prayer_times(city, tomorrow_date)

    if not today_data:
        await update.message.reply_text("❌ Vaqtlarni olishda xato. Keyinroq urining.")
        return

    timings = today_data["timings"]
    hijri = today_data["date"]["hijri"]
    gregorian = today_data["date"]["gregorian"]

    text = (
        f"📍 *{city}*\n"
        f"📅 {gregorian['date']} | {hijri['day']} {hijri['month']['en']} {hijri['year']}\n\n"
        f"🕌 *Bugungi namoz vaqtlari:*\n\n"
        f"🌅 Bomdod (Fajr):    `{timings['Fajr']}`\n"
        f"☀️ Quyosh:           `{timings['Sunrise']}`\n"
        f"🌞 Peshin (Dhuhr):  `{timings['Dhuhr']}`\n"
        f"🕒 Asr:              `{timings['Asr']}`\n"
        f"🌆 Shom (Maghrib):  `{timings['Maghrib']}`\n"
        f"🌙 Xufton (Isha):   `{timings['Isha']}`\n"
    )

    if tomorrow_data:
        tom_fajr = tomorrow_data["timings"]["Fajr"]
        text += f"\n📅 *Ertangi bomdod:* `{tom_fajr}`"

    await update.message.reply_text(text, parse_mode="Markdown")

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.from_user.id
    user = db_get_user(chat_id)
    if not user:
        await update.message.reply_text("Iltimos, /start yuboring.")
        return

    streak = user.get("streak_days", 0) or 0
    prayed = user.get("total_prayed", 0) or 0
    missed = user.get("total_missed", 0) or 0
    total = prayed + missed
    percent = (prayed / total * 100) if total > 0 else 0

    text = (
        f"📊 *Sizning statistikangiz*\n\n"
        f"🔥 Ketma-ket o'qigan kun: *{streak}* kun\n"
        f"✅ Jami o'qigan namozlar: *{prayed}*\n"
        f"⏰ Qo'ldan ketgan: *{missed}*\n"
        f"📈 Foiz: *{percent:.1f}%*\n\n"
    )
    if streak >= 7:
        text += "🌟 Mashallah! Davom eting!"
    elif streak >= 3:
        text += "💪 Yaxshi! Davom eting!"
    else:
        text += "🤲 Allohdan yordam so'rang."

    await update.message.reply_text(text, parse_mode="Markdown")

async def show_qibla(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.from_user.id
    user = db_get_user(chat_id)
    if not user:
        await update.message.reply_text("Iltimos, /start yuboring.")
        return

    city = user["city"]
    direction = get_qibla(city)
    if direction is None:
        await update.message.reply_text("❌ Qibla yo'nalishini olib bo'lmadi.")
        return

    text = (
        f"🧭 *Qibla yo'nalishi*\n\n"
        f"📍 {city} dan Makka tomon:\n"
        f"🧭 *{direction:.1f}°* (shimoldan o'ng tomon)\n\n"
        f"💡 Telefondagi kompasda shu darajani toping va o'sha tomonga yuzlaning."
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def show_hadith(update: Update, context: ContextTypes.DEFAULT_TYPE):
    today = datetime.now(TZ).date()
    idx = today.toordinal() % len(HADITHS)
    hadith = HADITHS[idx]

    text = (
        f"📖 *Bugungi hadis*\n"
        f"📅 {today.strftime('%d.%m.%Y')}\n\n"
        f"{hadith}"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def show_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🏙️ Shaharni o'zgartirish", callback_data="change_city")],
        [InlineKeyboardButton("🛑 Botni to'xtatish", callback_data="stop_bot")]
    ]
    await update.message.reply_text(
        "⚙️ *Sozlamalar:*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except BadRequest:
        return

    if query.data == "change_city":
        await show_city_selection(update, context)
    elif query.data == "stop_bot":
        chat_id = query.from_user.id
        db_create_or_update_user(chat_id, agreed=False)
        await query.edit_message_text(
            "🛑 Avtomatik xabarlar to'xtatildi.\n\n"
            "Qayta yoqish uchun /start yuboring."
        )

async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.from_user.id
    db_create_or_update_user(chat_id, agreed=False)
    await update.message.reply_text(
        "🛑 Avtomatik xabarlar to'xtatildi.\n\n"
        "Qayta yoqish uchun /start yuboring.",
        reply_markup=ReplyKeyboardRemove()
    )

# =========================
# 📩 NAMOZ TASDIQLASH HANDLER
# =========================
async def prayer_check_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except BadRequest:
        return

    chat_id = query.from_user.id
    user = db_get_user(chat_id)
    if not user:
        return

    parts = query.data.split("_")  # check_yes_Fajr yoki check_no_Fajr
    if len(parts) != 3:
        return
    answer = parts[1]
    prayer = parts[2]

    if answer == "yes":
        new_prayed = (user.get("total_prayed") or 0) + 1
        new_streak = (user.get("streak_days") or 0)
        # Bomdod o'qilgan bo'lsa streak +1
        if prayer == "Fajr":
            new_streak += 1
        db_create_or_update_user(
            chat_id,
            total_prayed=new_prayed,
            streak_days=new_streak
        )
        await query.edit_message_text(
            f"🌟 *Mashallah!*\n\n"
            f"Allohga shukr, {PRAYER_NAMES[prayer]} namozini o'qidingiz!\n"
            f"Allohdan barcha amallaringizni qabul qilishini so'raymiz. 🤲",
            parse_mode="Markdown"
        )
    else:
        new_missed = (user.get("total_missed") or 0) + 1
        # Streak uziladi agar bomdod qoldirilsa
        new_streak = 0 if prayer == "Fajr" else (user.get("streak_days") or 0)
        db_create_or_update_user(
            chat_id,
            total_missed=new_missed,
            streak_days=new_streak
        )
        await query.edit_message_text(
            f"⏰ *Keyingi safar kechiktirmang.*\n\n"
            f"Alloh bizni namoz ahllaridan qilsin. 🤲\n"
            f"Tavba qilib, keyingi namozni o'qishga harakat qiling.",
            parse_mode="Markdown"
        )

# =========================
# 📩 MATN HANDLER (menyu tugmalari)
# =========================
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    text = update.message.text.strip()
    chat_id = update.message.from_user.id
    user = db_get_user(chat_id)

    # Foydalanuvchi yo'q yoki rozilik bermagan
    if not user or not user.get("agreed"):
        await start(update, context)
        return

    # Menyu tugmalarini boshqarish
    if "namoz vaqtlari" in text.lower() or "🕌" in text:
        await show_prayer_times(update, context)
    elif "statistik" in text.lower() or "📊" in text:
        await show_stats(update, context)
    elif "qibla" in text.lower() or "🧭" in text:
        await show_qibla(update, context)
    elif "hadis" in text.lower() or "📖" in text:
        await show_hadith(update, context)
    elif "sozlama" in text.lower() or "⚙️" in text:
        await show_settings(update, context)
    else:
        await update.message.reply_text(
            "Iltimos, menyu tugmalaridan foydalaning yoki /start yuboring."
        )

# =========================
# 🛡️ XATO HANDLER
# =========================
async def error_handler(update, context):
    logging.error(f"Xato: {context.error}")

# =========================
# 🌐 FLASK + CRON ENDPOINT
# =========================
app_web = Flask(__name__)
bot_application = None  # global

@app_web.route("/")
def home():
    return "Namoz Bot ishlayapti ✅"

@app_web.route("/cron/<secret>")
def cron_endpoint(secret):
    """Cron-job.org har daqiqada shu URL'ni chaqiradi."""
    if secret != CRON_SECRET:
        return jsonify({"error": "unauthorized"}), 401

    try:
        # Asosiy bot loop'ida cron task'ini ishga tushirish
        if bot_application:
            asyncio.run_coroutine_threadsafe(
                run_cron_tasks(),
                bot_application.bot.loop if hasattr(bot_application.bot, 'loop') else asyncio.get_event_loop()
            )
        return jsonify({"status": "ok", "time": datetime.now(TZ).isoformat()})
    except Exception as e:
        logging.error(f"Cron xato: {e}")
        return jsonify({"error": str(e)}), 500

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app_web.run(host="0.0.0.0", port=port)

# =========================
# ⏰ AVTOMATIK XABAR LOGIKASI
# =========================
async def run_cron_tasks():
    """Har daqiqada chaqiriladi - kim qaysi xabarni olishi kerak?"""
    if not supabase:
        return

    now = datetime.now(TZ)
    current_time_str = now.strftime("%H:%M")
    today_date = now.date()

    users = db_get_all_agreed_users()
    if not users:
        return

    # Shahar bo'yicha guruhlash (API chaqiruvni kamaytirish)
    cities_data = {}

    for user in users:
        chat_id = user["chat_id"]
        city = user.get("city", "Toshkent")

        if city not in cities_data:
            cities_data[city] = get_prayer_times(city)
        prayer_data = cities_data[city]
        if not prayer_data:
            continue

        timings = prayer_data["timings"]

        # 1. Kunlik xulosa - 03:00 da
        if current_time_str == "03:00":
            last_summary = user.get("daily_summary_sent_date")
            if last_summary != today_date.isoformat():
                await send_daily_summary(chat_id, city, prayer_data)
                db_create_or_update_user(
                    chat_id,
                    daily_summary_sent_date=today_date.isoformat()
                )

        # 2. Namoz vaqti kelganda
        for prayer in PRAYER_ORDER:
            if timings[prayer] == current_time_str:
                await send_prayer_notification(chat_id, prayer, city)
                db_create_or_update_user(
                    chat_id,
                    last_prayer_asked=prayer,
                    last_prayer_time=now.isoformat()
                )

        # 3. Keyingi namozdan 5 daqiqa oldin - "O'qidingizmi?"
        for i, prayer in enumerate(PRAYER_ORDER):
            prayer_time_str = timings[prayer]
            try:
                ph, pm = map(int, prayer_time_str.split(":"))
                prayer_dt = now.replace(hour=ph, minute=pm, second=0, microsecond=0)
                check_dt = prayer_dt - timedelta(minutes=5)
                if check_dt.strftime("%H:%M") == current_time_str and i > 0:
                    prev_prayer = PRAYER_ORDER[i-1]
                    if user.get("last_prayer_asked") == prev_prayer:
                        await send_prayer_check(chat_id, prev_prayer)
            except Exception as e:
                logging.error(f"Time parse: {e}")

async def send_daily_summary(chat_id, city, prayer_data):
    timings = prayer_data["timings"]
    hijri = prayer_data["date"]["hijri"]
    gregorian = prayer_data["date"]["gregorian"]
    text = (
        f"🌅 *Yangi kun muborak!*\n\n"
        f"📍 {city}\n"
        f"📅 {gregorian['date']} | {hijri['day']} {hijri['month']['en']} {hijri['year']}\n\n"
        f"🕌 *Bugungi namoz vaqtlari:*\n\n"
        f"🌅 Bomdod:    `{timings['Fajr']}`\n"
        f"🌞 Peshin:   `{timings['Dhuhr']}`\n"
        f"🕒 Asr:       `{timings['Asr']}`\n"
        f"🌆 Shom:     `{timings['Maghrib']}`\n"
        f"🌙 Xufton:   `{timings['Isha']}`\n\n"
        f"🤲 Allohdan barcha amallarimizni qabul qilishini so'raymiz."
    )
    try:
        await bot_application.bot.send_message(chat_id, text, parse_mode="Markdown")
    except Forbidden:
        db_create_or_update_user(chat_id, agreed=False)
    except Exception as e:
        logging.error(f"Daily summary xato: {e}")

async def send_prayer_notification(chat_id, prayer, city):
    text = (
        f"🕌 *{PRAYER_NAMES[prayer]} namozi vaqti boldi!*\n\n"
        f"📍 {city}\n\n"
        f"🤲 Allohu akbar! Namoz o'qishga shoshiling."
    )
    try:
        await bot_application.bot.send_message(chat_id, text, parse_mode="Markdown")
    except Forbidden:
        db_create_or_update_user(chat_id, agreed=False)
    except Exception as e:
        logging.error(f"Prayer notif xato: {e}")

async def send_prayer_check(chat_id, prayer):
    keyboard = [
        [
            InlineKeyboardButton("✅ Ha, o'qidim", callback_data=f"check_yes_{prayer}"),
            InlineKeyboardButton("❌ Yo'q", callback_data=f"check_no_{prayer}")
        ]
    ]
    text = f"❓ *{PRAYER_NAMES[prayer]} namozini o'qidingizmi?*"
    try:
        await bot_application.bot.send_message(
            chat_id,
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
    except Forbidden:
        db_create_or_update_user(chat_id, agreed=False)
    except Exception as e:
        logging.error(f"Prayer check xato: {e}")

# =========================
# 🤖 ASOSIY
# =========================
def main():
    global bot_application

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    except Exception:
        pass

    Thread(target=run_web, daemon=True).start()

    app = ApplicationBuilder().token(TOKEN).build()
    bot_application = app

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stop", stop_command))
    app.add_handler(CallbackQueryHandler(agreement_callback, pattern="^agree_"))
    app.add_handler(CallbackQueryHandler(city_callback, pattern="^city_"))
    app.add_handler(CallbackQueryHandler(settings_callback, pattern="^(change_city|stop_bot)$"))
    app.add_handler(CallbackQueryHandler(prayer_check_callback, pattern="^check_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    app.add_error_handler(error_handler)

    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
