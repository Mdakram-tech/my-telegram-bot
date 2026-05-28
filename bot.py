import os
import asyncio
import requests
import yt_dlp  # Fixed: Missing import add kiya
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# Folder check
if not os.path.exists('downloads'):
    os.makedirs('downloads')

# 1. Start Command (Buttons ke sath)
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("🇮🇳 Hindi / Urdu", callback_data='lang_hi'),
            InlineKeyboardButton("🇬🇧 English", callback_data='lang_en')
        ],
        [
            InlineKeyboardButton("ℹ️ Help / Madad", callback_data='help_info'),
            InlineKeyboardButton("📢 About Bot", callback_data='about_bot')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "👋 Sallam / Welcome!\n\n"
        "Please select your language or choose an option below:\n"
        "Koshish karen ke pehle apni zaban select kar lein 👇",
        reply_markup=reply_markup
    )

# 2. Buttons Par Click Hone Ke Baad Kya Hoga
async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == 'lang_hi':
        await query.edit_message_text(
            text="✅ **Zaban: Hindi / Urdu** select ho gayi hai.\n\n"
                 "📥 Ab aap kisi bhi video (YouTube, Instagram, Facebook) ka link yahan send karen, mein download kar doonga!"
        )
    elif query.data == 'lang_en':
        await query.edit_message_text(
            text="✅ **Language: English** has been selected.\n\n"
                 "📥 Now send any video link (YouTube, Instagram, Facebook) here, and I will download it for you!"
        )
    elif query.data == 'help_info':
        await query.edit_message_text(
            text="❓ **Madad / Help:**\n\n"
                 "1. Kisi bhi video ka share link copy karen.\n"
                 "2. Is chat mein paste karke send kar den.\n"
                 "3. Bot automatic process karke video bhej dega.\n\n"
                 "🔙 Wapas jaane ke liye /start likhen."
        )
    elif query.data == 'about_bot':
        await query.edit_message_text(
            text="🤖 **About Bot:**\n\n"
                 "Yeh ek High-Speed Video Downloader bot hai jo bilkul free hai.\n"
                 "Developed by: Mohammed Akram ✨"
        )

# 3. TeraBox Helper
def get_terabox_download_url(terabox_url):
    try:
        api_url = f"https://api.teraboxdownloader.workers.dev/?url={terabox_url}"
        response = requests.get(api_url, timeout=15)
        if response.status_code == 200:
            data = response.json()
            if "url" in data:
                return data["url"]
    except Exception:
        pass
    return None

# 4. Main Downloader Function (Long Video Timeouts Fixed)
async def download_and_send_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    status_message = await update.message.reply_text("Processing video... Badi videos mein thoda zyada time lag sakta hai ⏳")

    # TeraBox Handling
    if "terabox" in url or "nephobox" in url or "4shared" in url:
        loop = asyncio.get_event_loop()
        direct_link = await loop.run_in_executor(None, get_terabox_download_url, url)
        if direct_link:
            try:
                # Long video timeout protection for TeraBox direct links
                await update.message.reply_video(
                    video=direct_link, 
                    caption="Aapki TeraBox Video!",
                    read_timeout=600,
                    write_timeout=600
                )
                await status_message.delete()
                return
            except Exception:
                pass
        await status_message.edit_text("Error processing TeraBox link.")
        return

    # Normal Platforms (YouTube, Insta, FB)
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': 'downloads/%(id)s.%(ext)s',
        'quiet': True,
        'socket_timeout': 120,   # Network timeout ko 2 minute kiya taake bada file connection drop na ho
        'retries': 15,          # Retries badha di
        'restrictfilenames': True,
    }

    try:
        loop = asyncio.get_event_loop()
        def download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                return ydl.prepare_filename(info)

        file_path = await loop.run_in_executor(None, download)
        
        if not os.path.exists(file_path):
            base_path = file_path.rsplit('.', 1)[0]
            if os.path.exists(f"{base_path}.mp4"): file_path = f"{base_path}.mp4"
            elif os.path.exists(f"{base_path}.mkv"): file_path = f"{base_path}.mkv"

        await status_message.edit_text("Video download ho chuki hai! Ab Telegram par upload ho rahi hai... 📤")
        
        # Badi files upload karne ke liye read/write timeouts ko 10-10 minute (600s) kar diya
        with open(file_path, 'rb') as video_file:
            await update.message.reply_video(
                video=video_file, 
                caption="Done! 🎉 Aapki Video Tayar Hai.",
                read_timeout=600,  
                write_timeout=600  
            )

        os.remove(file_path)
        await status_message.delete()

    except Exception as e:
        print(f"Error: {e}")
        await status_message.edit_text("Maaf kijiyega, is link se video download nahi ho saki ya file bohot badi hai.")

# 5. Main Application Configuration (Web Server Configuration Fixed)
def main():
    TOKEN = "8885032483:AAEP39aEEg69lMYQ1veslKOi4ztbDRk0grY"
    
    # Base application build
    application = Application.builder().token(TOKEN).build()

    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_click))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_and_send_video))

    print("Bot chalu hai buttons aur long video support ke sath...")
    application.run_polling()

if __name__ == '__main__':
    main()
