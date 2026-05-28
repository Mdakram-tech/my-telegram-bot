import os
import asyncio
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import yt_dlp

# Folder agar nahi bana to automatic ban jaye
if not os.path.exists('downloads'):
    os.makedirs('downloads')

# 1. Start Command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Sallam! All Video Downloader Bot mein khush aamdeed.\n\n"
        "📥 Sirf video ka link copy karke yahan send karen!"
    )

# 2. TeraBox Downloader Helper
def get_terabox_download_url(terabox_url):
    try:
        api_url = f"https://api.teraboxdownloader.workers.dev/?url={terabox_url}"
        response = requests.get(api_url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if "url" in data:
                return data["url"]
    except Exception:
        pass
    return None

# 3. Main Video Downloader Function
async def download_and_send_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    status_message = await update.message.reply_text("Video process ho rahi hai, please thoda intezar karen...")

    # TeraBox Handling
    if "terabox" in url or "nephobox" in url or "4shared" in url:
        loop = asyncio.get_event_loop()
        direct_link = await loop.run_in_executor(None, get_terabox_download_url, url)
        if direct_link:
            try:
                await update.message.reply_video(video=direct_link, caption="Aapki TeraBox Video!")
                await status_message.delete()
                return
            except Exception:
                pass
        await status_message.edit_text("Maaf kijiyega, TeraBox link process nahi ho saka.")
        return

    # Normal Platforms (YouTube, Insta, FB)
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': 'downloads/%(id)s.%(ext)s', # Unique ID banata hai, lambe Arabic naam ka rola khatam
        'quiet': True,
        'socket_timeout': 30,
        'retries': 10,
        'restrictfilenames': True,
    }

    try:
        loop = asyncio.get_event_loop()
        
        def download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                return filename

        file_path = await loop.run_in_executor(None, download)
        
        # Extension fix agar merge ke baad badal jaye
        if not os.path.exists(file_path):
            base_path = file_path.rsplit('.', 1)[0]
            if os.path.exists(f"{base_path}.mp4"):
                file_path = f"{base_path}.mp4"
            elif os.path.exists(f"{base_path}.mkv"):
                file_path = f"{base_path}.mkv"

        await status_message.edit_text("Video download ho chuki hai! Ab Telegram par upload ho rahi hai...")
        
        with open(file_path, 'rb') as video_file:
            await update.message.reply_video(video=video_file, caption="Aapki video tayar hai!")

        os.remove(file_path)
        await status_message.delete()

    except Exception as e:
        print(f"Error: {e}")
        await status_message.edit_text("Maaf kijiyega, is link se video download nahi ho saki.")

def main():
    TOKEN = "8885032483:AAEP39aEEg69lMYQ1veslKOi4ztbDRk0grY"
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_and_send_video))
    print("Bot chal raha hai...")
    application.run_polling()

if __name__ == '__main__':
    main()