import os
import asyncio
import requests
import yt_dlp  
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# Create downloads folder if it does not exist
if not os.path.exists('downloads'):
    os.makedirs('downloads')

# Global Keyboard for auto-repeat menus
def get_main_keyboard():
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
    return InlineKeyboardMarkup(keyboard)

# 1. Start Command Handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply_markup = get_main_keyboard()
    await update.message.reply_text(
        "👋 Welcome to All Video Downloader Bot!\n\n"
        "Please select your language or choose an option below 👇",
        reply_markup=reply_markup
    )

# 2. Inline Button Click Handler
async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == 'lang_hi':
        await query.edit_message_text(
            text="✅ **Language: Hindi / Urdu** has been selected.\n\n"
                 "📥 Now send any video link (YouTube, Instagram, Facebook), and I will download it for you!"
        )
    elif query.data == 'lang_en':
        await query.edit_message_text(
            text="✅ **Language: English** has been selected.\n\n"
                 "📥 Now send any video link (YouTube, Instagram, Facebook), and I will download it for you!"
        )
    elif query.data == 'help_info':
        await query.edit_message_text(
            text="❓ **Help / Instructions:**\n\n"
                 "1. Copy the share link of any video.\n"
                 "2. Paste and send the link in this chat.\n"
                 "3. The bot will automatically process and send the video.\n\n"
                 "🔙 Type /start to go back to the main menu."
        )
    elif query.data == 'about_bot':
        await query.edit_message_text(
            text="🤖 **About Bot:**\n\n"
                 "This is a High-Speed Video Downloader bot, completely free to use.\n"
                 "Developed by: Mohammed Akram ✨"
        )

# 3. TeraBox API URL Extractor
def get_terabox_download_url(terabox_url):
    try:
        # Note: If you made your own Cloudflare worker, replace this link with yours
        api_url = f"https://api.teraboxdownloader.workers.dev/?url={terabox_url}"
        response = requests.get(api_url, timeout=15)
        if response.status_code == 200:
            data = response.json()
            if "url" in data:
                return data["url"]
    except Exception:
        pass
    return None

# 4. Main Downloader Function (Handles link safety & loops back)
async def download_and_send_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()

    # Link Validation Fix: Stops the bot from treating commands/text as links
    if not url.startswith("http://") and not url.startswith("https://"):
        await update.message.reply_text(
            "⚠️ **Invalid Link!**\n\n"
            "Please send a valid video URL (e.g., YouTube, Instagram, Facebook, or TeraBox link).\n"
            "Make sure it starts with http:// or https://",
            reply_markup=get_main_keyboard()
        )
        return

    status_message = await update.message.reply_text("Processing video... Large videos might take a little longer ⏳")

    # TeraBox Link Support (With Smart Direct Download Button Bypass)
    if "terabox" in url or "nephobox" in url or "4shared" in url or "mirrobox" in url:
        loop = asyncio.get_event_loop()
        direct_link = await loop.run_in_executor(None, get_terabox_download_url, url)
        
        if direct_link:
            try:
                await update.message.reply_video(
                    video=direct_link, 
                    caption="🚀 **Your TeraBox Video!**",
                    read_timeout=300,
                    write_timeout=300
                )
                await status_message.delete()
                
                # Auto-repeat prompt after success
                await update.message.reply_text(
                    "What would you like to do next? Choose an option below:",
                    reply_markup=get_main_keyboard()
                )
                return
            except Exception:
                # Triggers if video size exceeds Telegram's 50MB bot API download capability
                keyboard = [[InlineKeyboardButton("📥 Download Video File", url=direct_link)]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await status_message.edit_text(
                    "⚠️ **File Size Too Large!**\n\n"
                    "This video exceeds Telegram's 50MB limit for direct video transfers.\n\n"
                    "👉 Click the button below to download it directly at full speed!",
                    reply_markup=reply_markup
                )
                
                # Auto-repeat prompt after providing alternative link
                await update.message.reply_text(
                    "Ready for the next video? Choose an option:",
                    reply_markup=get_main_keyboard()
                )
                return
        
        await status_message.edit_text("Sorry, unable to process this TeraBox link. Please make sure the link is public.")
        return

    # Standard Platforms Configuration (YouTube, Instagram, Facebook)
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': 'downloads/%(id)s.%(ext)s',
        'quiet': True,
        'socket_timeout': 120,   
        'retries': 15,          
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

        await status_message.edit_text("Video downloaded successfully! Uploading to Telegram... 📤")
        
        with open(file_path, 'rb') as video_file:
            await update.message.reply_video(
                video=video_file, 
                caption="Done! 🎉 Your video is ready.",
                read_timeout=600,  
                write_timeout=600  
            )

        os.remove(file_path)
        await status_message.delete()

        # Auto-repeat prompt after standard platform success
        await update.message.reply_text(
            "What would you like to do next? Choose an option below:",
            reply_markup=get_main_keyboard()
        )

    except Exception as e:
        print(f"Error: {e}")
        await status_message.edit_text("Sorry, this link could not be downloaded or the file is too large.")

# 5. Application Launch Configuration
def main():
    TOKEN = "8885032483:AAEP39aEEg69lMYQ1veslKOi4ztbDRk0grY"
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_click))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_and_send_video))

    print("Bot is running with buttons and long video support...")
    application.run_polling()

if __name__ == '__main__':
    main()
