import os
import telebot
import yt_dlp

# --- SOZLAMALAR ---
# Render Environment Variables bo'limidan oladi
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "🔥 Salom! Men yangi Universal Yuklagichman.\n\n"
                                     "Menga qo'shiq nomini yozing yoki YouTube/TikTok havolasini yuboring!")

@bot.message_handler(content_types=['text'])
def handle_text(message):
    url = message.text
    chat_id = message.chat.id
    
    msg = bot.send_message(chat_id, "⏳ Qidirilmoqda va yuklanmoqda...")
    
    try:
        # SoundCloud orqali qidirish (Bloklanmaslik uchun)
        if "http" not in url:
            search_query = f"scsearch1:{url}"
        else:
            search_query = url

        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': 'downloaded_music.%(ext)s',
            # YouTube blokini aylanib o'tish
            'extractor_args': {'youtube': {'player_client': ['android']}},
            'quiet': True
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(search_query, download=True)
            if 'entries' in info:
                info = info['entries'][0]
            file_name = ydl.prepare_filename(info)

        with open(file_name, 'rb') as audio:
            bot.send_audio(chat_id, audio, caption=info.get('title', 'Yuklandi ✅'))
        
        os.remove(file_name)
        bot.delete_message(chat_id, msg.message_id)

    except Exception as e:
        bot.edit_message_text(f"❌ Xatolik: {str(e)}", chat_id, msg.message_id)

print("Bot ishga tushdi...")
bot.infinity_polling()
