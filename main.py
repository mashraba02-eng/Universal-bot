import os
import telebot
import yt_dlp
import sqlite3
from telebot import types

# --- SOZLAMALAR ---
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_ID = 5194764417
bot = telebot.TeleBot(TOKEN)

# --- MA'LUMOTLAR BAZASI ---
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

# --- BOT BUYRUQLARINI O'RNATISH (KO'K MENU) ---
bot.set_my_commands([
    telebot.types.BotCommand("/start", "Botni qayta ishga tushirish"),
    telebot.types.BotCommand("/help", "Yordam va yo'riqnoma"),
    telebot.types.BotCommand("/lang", "Tilni o'zgartirish")
])

# --- MATNLAR ---
messages = {
    'uz': {
        'welcome': "🔥 **Assalomu alaykum!**\n\nMenga havola yuboring, men uni yuklab beraman!",
        'help': "ℹ️ **Yordam**\n\n1. Instagram, TikTok, YouTube yoki FB'dan havola nusxalang.\n2. Havolani menga yuboring.\n3. Bir necha soniya kuting!",
        'lang_select': "Tilni tanlang:",
        'searching': "🔍 Qidirilmoqda...",
        'main_menu': "Asosiy menyu",
        'btn_lang': "🌐 Tilni o'zgartirish",
        'btn_help': "❓ Yordam"
    },
    'ru': {
        'welcome': "🔥 **Привет!**\n\nОтправьте мне ссылку, и я скачаю её!",
        'help': "ℹ️ **Помощь**\n\n1. Скопируйте ссылку.\n2. Отправьте её мне.\n3. Подождите пару секунд!",
        'lang_select': "Выберите язык:",
        'searching': "🔍 Поиск...",
        'main_menu': "Главное меню",
        'btn_lang': "🌐 Сменить язык",
        'btn_help': "❓ Помощь"
    },
    'en': {
        'welcome': "🔥 **Hello!**\n\nSend me a link, and I will download it!",
        'help': "ℹ️ **Help**\n\n1. Copy the link.\n2. Send it to me.\n3. Wait a few seconds!",
        'lang_select': "Select language:",
        'searching': "🔍 Searching...",
        'main_menu': "Main menu",
        'btn_lang': "🌐 Change Language",
        'btn_help': "❓ Help"
    }
}

user_languages = {}

# --- TUGMALAR ---
def get_lang_keyboard():
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("🇺🇿 O'zbekcha", callback_data="lang_uz"),
                 types.InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"),
                 types.InlineKeyboardButton("🇺🇸 English", callback_data="lang_en"))
    return keyboard

def get_main_menu(lang):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(messages[lang]['btn_help'], messages[lang]['btn_lang'])
    return markup

# --- ADMIN PANEL ---
@bot.message_handler(commands=['panel'])
def admin_panel(message):
    if message.from_user.id == ADMIN_ID:
        count = len(get_all_users())
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("📊 Statistika", "📢 Reklama")
        bot.send_message(message.chat.id, f"🛠 **Admin Panel**\n\nFoydalanuvchilar: {count} ta", reply_markup=markup)

# --- ASOSIY BUYRUQLAR ---
@bot.message_handler(commands=['start'])
def start(message):
    add_user(message.from_user.id)
    bot.send_message(message.chat.id, "🇺🇿 Tilni tanlang / 🇷🇺 Выберите язык / 🇺🇸 Select language:", reply_markup=get_lang_keyboard())

@bot.message_handler(commands=['help'])
@bot.message_handler(func=lambda m: m.text in ["❓ Yordam", "❓ Помощь", "❓ Help"])
def help_cmd(message):
    lang = user_languages.get(message.chat.id, 'uz')
    bot.send_message(message.chat.id, messages[lang]['help'], parse_mode="Markdown")

@bot.message_handler(commands=['lang'])
@bot.message_handler(func=lambda m: m.text in ["🌐 Tilni o'zgartirish", "🌐 Сменить язык", "🌐 Change Language"])
def change_lang(message):
    bot.send_message(message.chat.id, messages['uz']['lang_select'], reply_markup=get_lang_keyboard())

@bot.callback_query_handler(func=lambda call: call.data.startswith('lang_'))
def set_language(call):
    lang = call.data.split('_')[1]
    user_languages[call.message.chat.id] = lang
    bot.delete_message(call.message.chat.id, call.message.message_id)
    bot.send_message(call.message.chat.id, messages[lang]['welcome'], 
                     reply_markup=get_main_menu(lang), parse_mode="Markdown")

# --- YUKLASH QISMI ---
@bot.message_handler(func=lambda message: "http" in message.text)
def handle_download(message):
    lang = user_languages.get(message.chat.id, 'uz')
    msg = bot.send_message(message.chat.id, messages[lang]['searching'])
    try:
        ydl_opts = {'format': 'best', 'outtmpl': 'downloads/%(title)s.%(ext)s', 'quiet': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(message.text, download=True)
            filename = ydl.prepare_filename(info)
        with open(filename, 'rb') as f:
            bot.send_video(message.chat.id, f)
        os.remove(filename)
        bot.delete_message(message.chat.id, msg.message_id)
    except:
        bot.send_message(message.chat.id, "❌ Error!")

bot.infinity_polling()
