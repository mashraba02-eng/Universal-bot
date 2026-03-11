import os
import sqlite3
import telebot
import yt_dlp
import requests
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, BotCommand, ReplyKeyboardMarkup, ReplyKeyboardRemove

# --- 1. API VA SOZLAMALAR ---
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
AUDD_API = os.getenv("AUDD_API")
ADMIN_ID = int(os.getenv("ADMIN_ID", 123456789))

bot = telebot.TeleBot(TOKEN)
DOWNLOAD_PATH = "downloads"

# Qidiruv natijalarini vaqtincha saqlash uchun lug'at (Yangi tizim)
SEARCH_RESULTS = {}

if not os.path.exists(DOWNLOAD_PATH):
    os.makedirs(DOWNLOAD_PATH)

# --- 2. MA'LUMOTLAR BAZASI ---
conn = sqlite3.connect('bot_database.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        chat_id INTEGER PRIMARY KEY, 
        lang TEXT DEFAULT 'uz',
        current_link TEXT
    )
''')
conn.commit()

def get_user(chat_id):
    cursor.execute("SELECT lang, current_link FROM users WHERE chat_id = ?", (chat_id,))
    row = cursor.fetchone()
    if not row:
        cursor.execute("INSERT INTO users (chat_id, lang) VALUES (?, ?)", (chat_id, 'uz'))
        conn.commit()
        return ('uz', None)
    return row

def update_lang(chat_id, lang):
    get_user(chat_id)
    cursor.execute("UPDATE users SET lang = ? WHERE chat_id = ?", (lang, chat_id))
    conn.commit()

def update_link(chat_id, link):
    get_user(chat_id)
    cursor.execute("UPDATE users SET current_link = ? WHERE chat_id = ?", (link, chat_id))
    conn.commit()

def get_all_users():
    cursor.execute("SELECT chat_id FROM users")
    return [row[0] for row in cursor.fetchall()]

# --- 3. KO'P TILLILIK LUG'ATI ---
LANG = {
    "uz": {
        "welcome": "🔥 **Universal Downloader botiga xush kelibsiz!**\n\n"
                   "Bot orqali quyidagilarni yuklab olishingiz mumkin:\n\n"
                   "• **Instagram** - post, Reels va IGTV + audio;\n"
                   "• **TikTok** - suv belgisiz video + audio;\n"
                   "• **YouTube** - video va audio;\n"
                   "• **Spotify/SoundCloud** kabi musiqalar qidiruvi;\n\n"
                   "🎧 **Shazam funksiyasi (Musiqa qidiruv):**\n"
                   "• Qo‘shiq nomi yoki ijrochi ismi orqali\n"
                   "• Ovozli xabar (Voice) orqali\n"
                   "• Audio fayl orqali\n\n"
                   "🚀 **Havolani yuboring yoki qo'shiq nomini yozing!**",
        "downloading": "⏳ Yuklanmoqda...",
        "song_not_found": "❌ Qo‘shiq topilmadi",
        "choose_format": "🔽 Formatni tanlang:",
        "video": "📹 Video",
        "audio": "🎵 Audio",
        "tt_video": "📹 Suv belgisiz",
        "tt_audio": "🎵 TikTok Musiqasi",
        "not_found": "❌ Topilmadi",
        "error": "❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring."
    },
    "ru": {
        "welcome": "🔥 **Добро пожаловать в Universal Downloader бот!**\n\n"
                   "Через бота вы можете скачивать медиа из соцсетей, а также искать музыку!\n\n"
                   "🚀 **Отправьте ссылку на видео или напишите название песни!**",
        "downloading": "⏳ Загрузка...",
        "song_not_found": "❌ Песня не найдена",
        "choose_format": "🔽 Выберите формат:",
        "video": "📹 Видео",
        "audio": "🎵 Аудио",
        "tt_video": "📹 Без водяного знака",
        "tt_audio": "🎵 Музыка из TikTok",
        "not_found": "❌ Не найдено",
        "error": "❌ Произошла ошибка."
    },
    "en": {
        "welcome": "🔥 **Welcome to Universal Downloader!**\n\n"
                   "Download media from social networks or search for music!\n\n"
                   "🚀 **Send a link or type a song name!**",
        "downloading": "⏳ Downloading...",
        "song_not_found": "❌ Song not found",
        "choose_format": "🔽 Choose format:",
        "video": "📹 Video",
        "audio": "🎵 Audio",
        "tt_video": "📹 No Watermark",
        "tt_audio": "🎵 TikTok Audio",
        "not_found": "❌ Not found",
        "error": "❌ An error occurred."
    }
}

def get_text(chat_id, key):
    lang, _ = get_user(chat_id)
    return LANG.get(lang, LANG["uz"])[key]

# --- 4. TELEGRAM MENYU YARATISH ---
bot.set_my_commands([
    BotCommand("start", "🔄 Botni qayta ishga tushirish"),
    BotCommand("lang", "🌍 Tilni o'zgartirish")
])

# --- 5. ADMIN PANEL ---
@bot.message_handler(commands=['stat'])
def stat_command(message):
    if message.chat.id == ADMIN_ID:
        users = get_all_users()
        bot.send_message(message.chat.id, f"📊 Bot statistikasi:\n\n👥 Jami foydalanuvchilar: {len(users)} ta")

@bot.message_handler(commands=['send'])
def send_command(message):
    if message.chat.id == ADMIN_ID:
        msg = bot.send_message(message.chat.id, "Barchaga yuboriladigan xabarni jo'nating:")
        bot.register_next_step_handler(msg, broadcast_message)

def broadcast_message(message):
    users = get_all_users()
    count = 0
    bot.send_message(ADMIN_ID, "⏳ Xabar yuborilmoqda, kuting...")
    for user_id in users:
        try:
            bot.copy_message(chat_id=user_id, from_chat_id=message.chat.id, message_id=message.message_id)
            count += 1
        except Exception:
            pass
    bot.send_message(ADMIN_ID, f"✅ Xabar muvaffaqiyatli {count} ta foydalanuvchiga yuborildi!")

# --- 6. START VA TILLAR ---
@bot.message_handler(commands=['start', 'lang'])
def start(message):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🇺🇿 O'zbek", "🇷🇺 Русский", "🇺🇸 English")
    bot.send_message(message.chat.id, "Tilni tanlang / Выберите язык / Choose language", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text in ["🇺🇿 O'zbek","🇷🇺 Русский","🇺🇸 English"])
def set_lang(message):
    chat_id = message.chat.id
    if "O'zbek" in message.text:
        update_lang(chat_id, "uz")
    elif "Русский" in message.text:
        update_lang(chat_id, "ru")
    else:
        update_lang(chat_id, "en")

    markup = ReplyKeyboardRemove()
    bot.send_message(chat_id, get_text(chat_id, "welcome"), reply_markup=markup, parse_mode="Markdown")

# --- 7. LINK VA MATN ORQALI QIDIRUV (SoundCloud Tizimi) ---
@bot.message_handler(content_types=['text'])
def handle_text(message):
    text = message.text
    chat_id = message.chat.id
    
    if text.startswith('/'):
        return

    # AGAR XABAR LINK BO'LSA
    if "http" in text:
        update_link(chat_id, text)
        markup = InlineKeyboardMarkup()

        if "youtube.com" in text or "youtu.be" in text:
            markup.add(
                InlineKeyboardButton("📹 360p", callback_data="yt_360"),
                InlineKeyboardButton("📹 720p", callback_data="yt_720")
            )
            markup.add(InlineKeyboardButton(get_text(chat_id, "audio"), callback_data="yt_audio"))
        elif "tiktok.com" in text or "vm.tiktok.com" in text:
            markup.add(
                InlineKeyboardButton(get_text(chat_id, "tt_video"), callback_data="tt_video"),
                InlineKeyboardButton(get_text(chat_id, "tt_audio"), callback_data="tt_audio")
            )
        else:
            markup.add(
                InlineKeyboardButton(get_text(chat_id, "video"), callback_data="yt_best"),
                InlineKeyboardButton(get_text(chat_id, "audio"), callback_data="yt_audio")
            )
        bot.send_message(chat_id, get_text(chat_id, "choose_format"), reply_markup=markup)

    # AGAR XABAR ODDIY SO'Z BO'LSA (SOUNDCLOUD ORQALI QIDIRUV)
    else:
        msg = bot.send_message(chat_id, "🔎 Qidirilmoqda, biroz kuting...")
        
        try:
            ydl_opts = {'extract_flat': True, 'quiet': True}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # YouTube o'rniga SoundCloud ulandi (scsearch10)
                info = ydl.extract_info(f"scsearch10:{text}", download=False)
            
            entries = info.get('entries', [])
            if not entries:
                bot.edit_message_text("❌ Hech narsa topilmadi.", chat_id, msg.message_id)
                return
            
            SEARCH_RESULTS[chat_id] = {}
            result_text = f"🎧 **{text}** qidiruv natijalari (SoundCloud):\n\n"
            markup = InlineKeyboardMarkup(row_width=5)
            buttons = []
            
            for i, entry in enumerate(entries):
                duration_sec = entry.get('duration')
                if duration_sec:
                    mins, secs = divmod(int(duration_sec), 60)
                    duration_str = f"{mins}:{secs:02d}"
                else:
                    duration_str = "Noma'lum"
                    
                title = entry.get('title', 'Nomsiz')
                url = entry.get('url')
                
                SEARCH_RESULTS[chat_id][str(i+1)] = url
                result_text += f"**{i+1}.** {title} ⏱ {duration_str}\n"
                buttons.append(InlineKeyboardButton(str(i+1), callback_data=f"dlm_{i+1}"))
            
            markup.add(*buttons)
            bot.delete_message(chat_id, msg.message_id)
            bot.send_message(chat_id, result_text, reply_markup=markup, parse_mode="Markdown")
            
        except Exception as e:
            bot.delete_message(chat_id, msg.message_id)
            bot.send_message(chat_id, get_text(chat_id, "error"))

# --- 8. TUGMALARNI (CALLBACK) BOSHQARISH ---
@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    chat_id = call.message.chat.id
    bot.answer_callback_query(call.id)
    
    # SOUNDCLOUD QIDIRUV RO'YXATIDAN TUGMA BOSILSA
    if call.data.startswith("dlm_"):
        idx = call.data.split("_")[1]
        url = SEARCH_RESULTS.get(chat_id, {}).get(idx)
        
        if not url:
            bot.answer_callback_query(call.id, "❌ Qidiruv eskirgan, matnni qayta yozib qidiring!", show_alert=True)
            return
            
        bot.edit_message_text(get_text(chat_id, "downloading"), chat_id, call.message.message_id)
        ytdlp_download(chat_id, url, format_type="audio")
        return
        
    # QOLGAN ODDIY LINK TUGMALARI UCHUN
    _, url = get_user(chat_id)
    if not url:
        bot.send_message(chat_id, get_text(chat_id, "error"))
        return

    bot.delete_message(chat_id, call.message.message_id)
    bot.send_message(chat_id, get_text(chat_id, "downloading"))

    if call.data == "yt_360":
        ytdlp_download(chat_id, url, format_type="360")
    elif call.data == "yt_720":
        ytdlp_download(chat_id, url, format_type="720")
    elif call.data == "yt_best":
        ytdlp_download(chat_id, url, format_type="best")
    elif call.data == "yt_audio":
        ytdlp_download(chat_id, url, format_type="audio")
    elif call.data == "tt_video":
        tiktok_download(chat_id, url, type="video")
    elif call.data == "tt_audio":
        tiktok_download(chat_id, url, type="audio")
    elif call.data == "shazam_dl":
        ytdlp_download(chat_id, url, format_type="audio")

# --- 9. YUKLASH FUNKSIYALARI ---
def ytdlp_download(chat_id, url, format_type):
    try:
        if format_type == "360":
            ydl_opts = {"format": "best[height<=360]/best", "outtmpl": f"{DOWNLOAD_PATH}/%(title)s_%(id)s.%(ext)s"}
        elif format_type == "720":
            ydl_opts = {"format": "best[height<=720]/best", "outtmpl": f"{DOWNLOAD_PATH}/%(title)s_%(id)s.%(ext)s"}
        elif format_type == "best":
            ydl_opts = {"format": "best", "outtmpl": f"{DOWNLOAD_PATH}/%(title)s_%(id)s.%(ext)s"}
        else:
            # Sof audio yuklash (FFmpeg xatosi bermaydi)
            ydl_opts = {
                "format": "bestaudio/best",
                "outtmpl": f"{DOWNLOAD_PATH}/%(title)s_%(id)s.%(ext)s"
            }

        # Agar foydalanuvchi YT link tashlasa deb qoldirildi
        ydl_opts['extractor_args'] = {'youtube': {'player_client': ['android']}}

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file = ydl.prepare_filename(info)

        if format_type == "audio":
            with open(file, "rb") as a:
                bot.send_audio(chat_id, a)
        else:
            with open(file, "rb") as v:
                bot.send_video(chat_id, v)
                
        os.remove(file)
    except Exception as e:
        print(f"Xatolik: {e}")
        bot.send_message(chat_id, get_text(chat_id, "error"))

def tiktok_download(chat_id, url, type):
    try:
        api_url = f"https://api.tiklydown.eu.org/api/download?url={url}"
        r = requests.get(api_url).json()

        if r.get("status") == 200:
            if type == "video":
                bot.send_video(chat_id, r["video"]["noWatermark"])
            elif type == "audio":
                bot.send_audio(chat_id, r["music"]["play_url"])
        else:
            bot.send_message(chat_id, get_text(chat_id, "not_found"))
    except Exception:
        bot.send_message(chat_id, get_text(chat_id, "error"))

# --- 10. SHAZAM FUNKSIYASI ---
@bot.message_handler(content_types=['audio', 'voice'])
def shazam(message):
    chat_id = message.chat.id
    temp_filename = f"temp_{chat_id}.mp3"
    msg = bot.send_message(chat_id, get_text(chat_id, "downloading"))

    try:
        file_id = message.audio.file_id if message.audio else message.voice.file_id
        file_info = bot.get_file(file_id)
        downloaded = bot.download_file(file_info.file_path)

        with open(temp_filename, "wb") as f:
            f.write(downloaded)

        response = requests.post(
            "https://api.audd.io/",
            data={"api_token": AUDD_API},
            files={"file": open(temp_filename, "rb")}
        )
        result = response.json()

        if result.get("result"):
            title = result['result']['title']
            artist = result['result']['artist']
            
            # Shazam ham endi xavfsiz SoundCloud dan qidiradi
            search_query = f"scsearch1:{artist} - {title}"
            update_link(chat_id, search_query)

            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("📥 Qo'shiqni yuklab olish", callback_data="shazam_dl"))

            bot.delete_message(chat_id, msg.message_id)
            bot.send_message(
                chat_id, 
                f"🎵 Qo'shiq: {title}\n👤 Ijrochi: {artist}", 
                reply_markup=markup
            )
        else:
            bot.delete_message(chat_id, msg.message_id)
            bot.send_message(chat_id, get_text(chat_id, "song_not_found"))
            
    except Exception:
        bot.send_message(chat_id, get_text(chat_id, "error"))
    finally:
        if os.path.exists(temp_filename):
            os.remove(temp_filename)

print("Bot ishlayapti...")
bot.infinity_polling()
