import os
import telebot
import yt_dlp
import sqlite3
import asyncio
from flask import Flask
from threading import Thread
from telebot import types
from shazam_helper import identify_track

# --- SERVER (Uptime Robot uchun) ---
app = Flask('')
@app.route('/')
def home(): return "Bot 24/7 holatda ishlamoqda!"

def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive():
    t = Thread(target=run)
    t.start()

# --- SOZLAMALAR ---
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_ID = 5194764417  # Sizning ID raqamingiz
bot = telebot.TeleBot(TOKEN)

# --- MATNLAR LUG'ATI ---
messages = {
    'uz': {
        'welcome': "🔥 **Assalomu alaykum!**\n\nMenga havola yuboring yoki ovozli xabar orqali qo'shiqni toping!",
        'searching': "🔍 Qidirilmoqda...",
        'success': "✅ Tayyor!",
        'error': "❌ Xatolik yuz berdi.",
        'lang_select': "Tilni tanlang:",
        'help_btn': "❓ Yordam",
        'lang_btn': "🌐 Tilni o'zgartirish",
        'help_text': "📖 **Yo'riqnoma:**\n1. Video yuklash uchun havolani yuboring.\n2. Musiqa topish uchun ovozli xabar yuboring."
    },
    'ru': {
        'welcome': "🔥 **Привет!**\n\nОтправьте мне ссылку или найдите песню через голосовое сообщение!",
        'searching': "🔍 Поиск...",
        'success': "✅ Готово!",
        'error': "❌ Произошла ошибка.",
        'lang_select': "Выберите язык:",
        'help_btn': "❓ Помощь",
        'lang_btn': "🌐 Сменить язык",
        'help_text': "📖 **Инструкция:**\n1. Отправьте ссылку для скачивания видео.\n2. Отправьте голосовое сообщение, чтобы найти музыку."
    },
    'en': {
        'welcome': "🔥 **Hello!**\n\nSend me a link or find a song via voice message!",
        'searching': "🔍 Searching...",
        'success': "✅ Done!",
        'error': "❌ An error occurred.",
        'lang_select': "Select language:",
        'help_btn': "❓ Help",
        'lang_btn': "🌐 Change Language",
        'help_text': "📖 **Manual:**\n1. Send a link to download the video.\n2. Send a voice message to find music."
    }
}

user_languages = {}

# --- BAZA ---
def add_user(user_id):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)')
    cursor.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (user_id,))
    conn.commit()
    conn.close()

def get_users_count():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM users')
    count = cursor.fetchone()[0]
    conn.close()
    return count

# --- TUGMALAR ---
def get_lang_keyboard():
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("🇺🇿 O'zbekcha", callback_data="lang_uz"),
                 types.InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"),
                 types.InlineKeyboardButton("🇺🇸 English", callback_data="lang_en"))
    return keyboard

def get_main_menu(lang):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(messages[lang]['help_btn'], messages[lang]['lang_btn'])
    return markup

# --- ADMIN PANEL ---
@bot.message_handler(commands=['panel'])
def admin_panel(message):
    if message.from_user.id == ADMIN_ID:
        count = get_users_count()
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("📊 Statistika", "📢 Reklama", "🏠 Asosiy Menyu")
        bot.send_message(message.chat.id, f"🛠 **Admin Panel**\n\nFoydalanuvchilar: {count} ta", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "📊 Statistika")
def stat(message):
    if message.from_user.id == ADMIN_ID:
        bot.send_message(message.chat.id, f"👥 Jami foydalanuvchilar: {get_users_count()}")

@bot.message_handler(func=lambda m: m.text == "🏠 Asosiy Menyu")
def back_home(message):
    lang = user_languages.get(message.chat.id, 'uz')
    bot.send_message(message.chat.id, "Asosiy menyuga qaytdingiz.", reply_markup=get_main_menu(lang))

# --- ASOSIY ISHLASH ---
@bot.message_handler(commands=['start'])
def start(message):
    add_user(message.from_user.id)
    bot.send_message(message.chat.id, "🇺🇿 Tilni tanlang / 🇷🇺 Выберите язык / 🇺🇸 Select language:", reply_markup=get_lang_keyboard())

@bot.callback_query_handler(func=lambda call: call.data.startswith('lang_'))
def set_language(call):
    lang = call.data.split('_')[1]
    user_languages[call.message.chat.id] = lang
    bot.delete_message(call.message.chat.id, call.message.message_id)
    bot.send_message(call.message.chat.id, messages[lang]['welcome'], reply_markup=get_main_menu(lang), parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text in ["❓ Yordam", "❓ Помощь", "❓ Help"])
def help_handler(message):
    lang = user_languages.get(message.chat.id, 'uz')
    bot.send_message(message.chat.id, messages[lang]['help_text'], parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text in ["🌐 Tilni o'zgartirish", "🌐 Сменить язык", "🌐 Change Language"])
def lang_change_handler(message):
    bot.send_message(message.chat.id, "🌐:", reply_markup=get_lang_keyboard())

# --- SHAZAM & YUKLAGICH ---
@bot.message_handler(content_types=['voice', 'audio'])
def handle_audio(message):
    lang = user_languages.get(message.chat.id, 'uz')
    msg = bot.send_message(message.chat.id, messages[lang]['searching'])
    try:
        file_info = bot.get_file(message.voice.file_id if message.voice else message.audio.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        with open("sh_temp.ogg", "wb") as f: f.write(downloaded_file)
        track = asyncio.run(identify_track("sh_temp.ogg"))
        if track:
            bot.send_message(message.chat.id, f"🎵 **{track['title']}**\n👤 **{track['author']}**", parse_mode="Markdown")
        else: bot.send_message(message.chat.id, "❌")
        os.remove("sh_temp.ogg")
        bot.delete_message(message.chat.id, msg.message_id)
    except: bot.send_message(message.chat.id, messages[lang]['error'])

@bot.message_handler(func=lambda m: "http" in m.text)
def handle_link(message):
    lang = user_languages.get(message.chat.id, 'uz')
    msg = bot.send_message(message.chat.id, messages[lang]['searching'])
    try:
        ydl_opts = {'format': 'best', 'outtmpl': 'downloads/%(title)s.%(ext)s', 'quiet': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(message.text, download=True)
            filename = ydl.prepare_filename(info)
        with open(filename, 'rb') as f: bot.send_video(message.chat.id, f)
        os.remove(filename)
        bot.delete_message(message.chat.id, msg.message_id)
    except: bot.send_message(message.chat.id, messages[lang]['error'])

if __name__ == '__main__':
    keep_alive()
    bot.infinity_polling()
