import os
import discord
from discord.ext import commands
import yt_dlp
import asyncio

# --- CẤU HÌNH ---
TOKEN = os.getenv('DISCORD_TOKEN')
TARGET_VOICE_CHANNEL = 'Music' 

DEFAULT_URL = 'https://www.youtube.com/watch?v=jfKfPfyJRdk'
YOUTUBE_URL = os.getenv('YOUTUBE_URL', DEFAULT_URL)

intents = discord.Intents.default()
intents.voice_states = True
intents.message_content = True
intents.members = True 
bot = commands.Bot(command_prefix='!', intents=intents)

# Cấu hình yt-dlp tối ưu
ytdl_opts = {
    'format': 'bestaudio/best',
    'quiet': True,
    'noplaylist': False,
    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'extract_flat': 'in_playlist',
}

# NÂNG CẤP 1: Cấu hình FFmpeg cực nhẹ để né lỗi -9 (kill process)
ffmpeg_opts = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn -b:a 128k -threads 1 -af "volume=0.8"' # Giảm tải CPU
}

@bot.event
async def on_ready():
    print(f'--- Vương Diệp Assistant Đã Sẵn Sàng ---')

@bot.event
async def on_voice_state_update(member, before, after):
    # 1. TỰ ĐỘNG VÀO VÀ PHÁT NHẠC
    if after.channel is not None and after.channel.name == TARGET_VOICE_CHANNEL and not member.bot:
        vc = member.guild.voice_client
        if vc is None:
            try:
                # NÂNG CẤP 2: Tăng timeout và thêm self_deaf để giữ kết nối ổn định hơn
                vc = await after.channel.connect(timeout=60.0, reconnect=True, self_deaf=True)
                print(f"✅ Đã vào phòng: {after.channel.name}")
            except Exception as e:
                print(f"❌ Lỗi kết nối Voice: {e}")
                return
        
        if not vc.is_playing():
            try:
                # NÂNG CẤP 3: Dọn dẹp triệt để tiến trình cũ trước khi phát mới
                if vc.source:
                    try:
                        vc.source.cleanup()
                    except:
                        pass

                loop = asyncio.get_event_loop()
                
                def fetch_info():
                    with yt_dlp.YoutubeDL(ytdl_opts) as ydl:
                        return ydl.extract_info(YOUTUBE_URL, download=False)

                print(f"⏳ Đang xử lý link: {YOUTUBE_URL}")
                info = await loop.run_in_executor(None, fetch_info)
                
                if info is None:
                    print("❌ Lỗi: Không lấy được dữ liệu.")
                    return

                url2 = None
                title = "Unknown Title"

                if 'entries' in info:
                    print("📂 Đang xử lý danh sách phát...")
                    entry = info['entries'][0]
                    if 'url' not in entry or 'formats' not in entry:
                        with yt_dlp.YoutubeDL(ytdl_opts) as ydl:
                            entry = ydl.extract_info(entry['url'], download=False)
                    url2 = entry.get('url')
                    title = entry.get('title')
                else:
                    url2 = info.get('url')
                    title = info.get('title')

                if not url2 and 'formats' in info:
                    url2 = info['formats'][0]['url']

                if url2:
                    # Khởi tạo source nhạc với cấu hình đã tối ưu
                    source = discord.FFmpegOpusAudio(url2, **ffmpeg_opts)
                    vc.play(source)
                    print(f"🎵 Đã lên nhạc: {title}")
                else:
                    print("❌ Không tìm thấy link stream.")
                
            except Exception as e:
                print(f"❌ Lỗi phát nhạc: {e}")

    # 2. TỰ ĐỘNG THOÁT KHI PHÒNG TRỐNG
    vc = member.guild.voice_client
    if vc and vc.channel:
        real_members = [m for m in vc.channel.members if not m.bot]
        if len(real_members) == 0:
            # Ngắt kết nối và dọn dẹp để không để lại tiến trình "rác"
            if vc.is_playing():
                vc.stop()
            await vc.disconnect()
            print("🚪 Phòng trống, Bot đã rút lui và dọn dẹp.")

if TOKEN:
    bot.run(TOKEN)
else:
    print("❌ LỖI: Thiếu DISCORD_TOKEN!")