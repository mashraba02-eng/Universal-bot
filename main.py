import os
import sqlite3
import telebot
import yt_dlp
import requests
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, BotCommand, ReplyKeyboardMarkup, ReplyKeyboardRemove
from flask import Flask
from threading import Thread

# --- 0. 24/7 ISHLASHI UCHUN WEB-SERVER (UPTIME) ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot ishlab turibdi!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- 1. API VA SOZLAMALAR ---
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
AUDD_API = os.getenv("AUDD_API")
ADMIN_ID = int(os.getenv("ADMIN_ID", 123456789)) # O'zingizning Telegram ID raqamingiz

bot = telebot.TeleBot(TOKEN)
DOWNLOAD_PATH = "downloads"

if not os.path.exists(DOWNLOAD_PATH):
    os.makedirs(DOWNLOAD_PATH)

# --- 2. MA'LUMOTLAR BAZASI (SQLite) ---
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
                   "• **YouTube** - video va MP3 formatlar;\n"
                   "• **Facebook** - video va audio;\n"
                   "• **Snapchat** - suv belgisiz video + audio;\n"
                   "• **Likee** - suv belgisiz video + audio;\n"
                   "• **Pinterest** - video va rasmlar + audio;\n\n"
                   "🎧 **Shazam funksiyasi (Musiqa qidiruv):**\n"
                   "• Qo‘shiq nomi yoki ijrochi ismi orqali\n"
                   "• Ovozli xabar (Voice) orqali\n"
                   "• Audio fayl (MP3) orqali\n\n"
                   "🚀 **Yuklab olmoqchi bo'lgan videoga havolani yuboring yoki qo'shiq nomini yozing!**\n"
                   "😎 **Bot guruhlarda ham ishlay oladi!**",
        "downloading": "⏳ Yuklanmoqda...",
        "song_not_found": "❌ Qo‘shiq topilmadi",
        "choose_format": "🔽 Formatni tanlang:",
        "video": "📹 Video",
        "audio": "🎵 MP3",
        "tt_video": "📹 Suv belgisiz (No Watermark)",
        "tt_audio": "🎵 TikTok Musiqasi",
        "not_found": "❌ Video yoki media topilmadi",
        "error": "❌ Xatolik yuz berdi. Fayl juda katta (50MB+) bo'lishi mumkin."
    },
    "ru": {
        "welcome": "🔥 **Добро пожаловать в Universal Downloader бот!**\n\n"
                   "Через бота вы можете скачивать:\n\n"
                   "• **Instagram** - посты, Reels и IGTV;\n"
                   "• **TikTok** - видео без водяного знака;\n"
                   "• **YouTube** - видео и MP3;\n"
                   "• **Facebook** - видео и аудио;\n"
                   "• **Snapchat, Likee, Pinterest** - медиа;\n\n"
                   "🎧 **Функция Shazam (Поиск музыки):**\n"
                   "• По названию песни или исполнителю\n"
                   "• Через голосовое сообщение (Voice)\n"
                   "• Через аудиофайл (MP3)\n\n"
                   "🚀 **Отправьте ссылку на видео или напишите название песни!**\n"
                   "😎 **Бот также работает в группах!**",
        "downloading": "⏳ Загрузка...",
        "song_not_found": "❌ Песня не найдена",
        "choose_format": "🔽 Выберите формат:",
        "video": "📹 Видео",
        "audio": "🎵 MP3",
        "tt_video": "📹 Без водяного знака",
        "tt_audio": "🎵 Музыка из TikTok",
        "not_found": "❌ Медиа не найдено",
        "error": "❌ Ошибка. Возможно, файл больше 50 МБ."
    },
    "en": {
        "welcome": "🔥 **Welcome to Universal Downloader bot!**\n\n"
                   "You can download from:\n\n"
                   "• **Instagram** - post, Reels, IGTV;\n"
                   "• **TikTok** - video without watermark;\n"
                   "• **YouTube** - video and MP3;\n"
                   "• **Facebook, Snapchat, Likee, Pinterest**;\n\n"
                   "🎧 **Shazam Function (Music Search):**\n"
                   "• By song name or artist\n"
                   "• Via voice message\n"
                   "• Via audio file\n\n"
                   "🚀 **Send a link to the video or type a song name!**\n"
                   "😎 **Bot also works in groups!**",
        "downloading": "⏳ Downloading...",
        "song_not_found": "❌ Song not found",
        "choose_format": "🔽 Choose format:",
        "video": "📹 Video",
        "audio": "🎵 MP3",
        "tt_video": "📹 No Watermark",
        "tt_audio": "🎵 TikTok Audio",
        "not_found": "❌ Media not found",
        "error": "❌ Error. File might be larger than 50MB."
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
        msg = bot.send_message(message.chat.id, "Barchaga yuboriladigan xabarni jo'nating (Rasm, video yoki matn):")
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

# --- 6. START VA TIL TANLASH ---
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

# --- 7. LINK VA MATN ORQALI QIDIRUV (TOP-10) ---
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

    # AGAR XABAR ODDIY SO'Z BO'LSA (10 TALIK QIDIRUV)
    else:
        msg = bot.send_message(chat_id, "🔎 Qidirilmoqda, biroz kuting...")
        
        try:
            ydl_opts = {'extract_flat': True, 'quiet': True}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(f"ytsearch10:{text}", download=False)
            
            entries = info.get('entries', [])
            if not entries:
                bot.edit_message_text("❌ Hech narsa topilmadi.", chat_id, msg.message_id)
                return
            
            result_text = f"🎧 **{text}** qidiruv natijalari:\n\n"
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
                video_id = entry.get('id')
                
                result_text += f"**{i+1}.** {title} ⏱ {duration_str}\n"
                buttons.append(InlineKeyboardButton(str(i+1), callback_data=f"dla_{video_id}"))
            
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
    
    # 1. QIDIRUV RO'YXATIDAN BIRORTASI BOSILSA
    if call.data.startswith("dla_"):
        video_id = call.data.split("_")[1]
        url = f"https://www.youtube.com/watch?v={video_id}"
        
        bot.edit_message_text(get_text(chat_id, "downloading"), chat_id, call.message.message_id)
        ytdlp_download(chat_id, url, format_type="audio")
        return
        
    # 2. QOLGAN ODDIY LINK TUGMALARI UCHUN
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
            ydl_opts = {
                "format": "bestaudio/best",
                "outtmpl": f"{DOWNLOAD_PATH}/%(title)s_%(id)s.%(ext)s",
                "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}]
            }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file = ydl.prepare_filename(info)

        if format_type == "audio":
            file = os.path.splitext(file)[0] + ".mp3"
            with open(file, "rb") as a:
                bot.send_audio(chat_id, a)
        else:
            with open(file, "rb") as v:
                bot.send_video(chat_id, v)
                
        os.remove(file)
    except Exception:
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

# --- 10. SHAZAM (QO'SHIQ ANIQLASH VA YUKLASH) ---
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
            
            search_query = f"ytsearch1:{artist} - {title} audio"
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

print("Bot va Web-server ishga tushirildi...")
keep_alive() # Web serverni ishga tushirish (Uptime uchun)
bot.infinity_polling()
