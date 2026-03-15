import os
import telebot
import yt_dlp
import sqlite3
from flask import Flask
from threading import Thread
from telebot import types

# --- SERVER QISMI (Uptime Robot uchun) ---
app = Flask('')

@app.route('/')
def home():
    return "Bot 24/7 holatda ishlamoqda!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- BOT SOZLAMALARI ---
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_ID = 5194764417
bot = telebot.TeleBot(TOKEN)

# --- BAZA BILAN ISHLASH ---
def db_init():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)')
    conn.commit()
    conn.close()

def add_user(user_id):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (user_id,))
    conn.commit()
    conn.close()

def get_all_users():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM users')
    users = cursor.fetchall()
    conn.close()
    return [u[0] for u in users]

db_init()

# KO'K MENU BUYRUQLARI
bot.set_my_commands([
    telebot.types.BotCommand("/start", "Ishga tushirish"),
    telebot.types.BotCommand("/panel", "Admin Panel (Faqat admin uchun)"),
    telebot.types.BotCommand("/lang", "Tilni o'zgartirish")
])

# MATNLAR
messages = {
    'uz': {
        'welcome': "🔥 **Assalomu alaykum!**\n\nMenga ijtimoiy tarmoqdan havola yuboring!",
        'lang_select': "Tilni tanlang:",
        'searching': "🔍 Yuklanmoqda...",
        'success': "✅ Tayyor!",
        'help': "❓ Yordam",
        'change_lang': "🌐 Tilni o'zgartirish"
    },
    'ru': {
        'welcome': "🔥 **Привет!**\n\nОтправьте мне ссылку из соцсетей!",
        'lang_select': "Выберите язык:",
        'searching': "🔍 Загрузка...",
        'success': "✅ Готово!",
        'help': "❓ Помощь",
        'change_lang': "🌐 Сменить язык"
    },
    'en': {
        'welcome': "🔥 **Hello!**\n\nSend me a link from social media!",
        'lang_select': "Select language:",
        'searching': "🔍 Downloading...",
        'success': "✅ Done!",
        'help': "❓ Help",
        'change_lang': "🌐 Change Language"
    }
}

user_languages = {}

# TUGMALAR
def get_lang_keyboard():
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("🇺🇿 O'zbekcha", callback_data="lang_uz"),
                 types.InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"),
                 types.InlineKeyboardButton("🇺🇸 English", callback_data="lang_en"))
    return keyboard

def get_main_menu(lang):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(messages[lang]['help'], messages[lang]['change_lang'])
    return markup

# --- ASOSIY FUNKSIYALAR ---
@bot.message_handler(commands=['start'])
def start(message):
    add_user(message.from_user.id)
    bot.send_message(message.chat.id, "🇺🇿 Tilni tanlang / 🇷🇺 Выберите язык / 🇺🇸 Select language:", reply_markup=get_lang_keyboard())

@bot.message_handler(commands=['panel'])
def admin_panel(message):
    if message.from_user.id == ADMIN_ID:
        count = len(get_all_users())
        bot.send_message(message.chat.id, f"🛠 **Admin Panel**\n\nFoydalanuvchilar: {count} ta\n\nReklama yuborish uchun xabarni menga yuboring (Hozircha faqat statistika).")

@bot.callback_query_handler(func=lambda call: call.data.startswith('lang_'))
def set_language(call):
    lang = call.data.split('_')[1]
    user_languages[call.message.chat.id] = lang
    bot.delete_message(call.message.chat.id, call.message.message_id)
    bot.send_message(call.message.chat.id, messages[lang]['welcome'], reply_markup=get_main_menu(lang), parse_mode="Markdown")

@bot.message_handler(func=lambda message: "http" in message.text)
def handle_download(message):
    lang = user_languages.get(message.chat.id, 'uz')
    msg = bot.send_message(message.chat.id, messages[lang]['searching'])
    
    try:
        ydl_opts = {
            'format': 'best',
            'outtmpl': 'downloads/%(title)s.%(ext)s',
            'quiet': True,
            'extractor_args': {'youtube': {'player_client': ['android']}},
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(message.text, download=True)
            filename = ydl.prepare_filename(info)

        with open(filename, 'rb') as f:
            bot.send_video(message.chat.id, f, caption=f"{messages[lang]['success']}")
        
        os.remove(filename)
        bot.delete_message(message.chat.id, msg.message_id)
    except Exception as e:
        bot.edit_message_text(f"❌ Xatolik yuz berdi. Havola noto'g'ri bo'lishi mumkin.", message.chat.id, msg.message_id)

# --- ISHGA TUSHIRISH ---
if __name__ == '__main__':
    keep_alive() # Serverni uyg'oq tutish
    print("Bot ishga tushdi...")
    bot.infinity_polling()
