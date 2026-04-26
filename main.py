import os
import discord
from discord.ext import commands
import yt_dlp
import asyncio

# --- CẤU HÌNH ---
TOKEN = os.getenv('DISCORD_TOKEN')
TARGET_VOICE_CHANNEL = 'Music' 

# Ưu tiên lấy URL từ biến YOUTUBE_URL trên Railway
DEFAULT_URL = 'https://www.youtube.com/watch?v=jfKfPfyJRdk'
YOUTUBE_URL = os.getenv('YOUTUBE_URL', DEFAULT_URL)

intents = discord.Intents.default()
intents.voice_states = True
intents.message_content = True
intents.members = True 
bot = commands.Bot(command_prefix='!', intents=intents)

# Cấu hình yt-dlp tối ưu (Tắt noplaylist để xử lý được cả link tập hợp)
ytdl_opts = {
    'format': 'bestaudio/best',
    'quiet': True,
    'noplaylist': False, # Cho phép đọc playlist để lấy bài đầu tiên
    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'extract_flat': 'in_playlist', # Chỉ lấy thông tin, không tải cả playlist
}

ffmpeg_opts = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
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
                vc = await after.channel.connect(timeout=30.0, reconnect=True)
            except Exception as e:
                print(f"Lỗi kết nối Voice: {e}")
                return
        
        if not vc.is_playing():
            try:
                loop = asyncio.get_event_loop()
                
                def fetch_info():
                    with yt_dlp.YoutubeDL(ytdl_opts) as ydl:
                        # Trích xuất thông tin bài hát
                        return ydl.extract_info(YOUTUBE_URL, download=False)

                print(f"⏳ Đang xử lý link: {YOUTUBE_URL}")
                info = await loop.run_in_executor(None, fetch_info)
                
                if info is None:
                    print("❌ Lỗi: Không lấy được dữ liệu.")
                    return

                # XỬ LÝ LẤY LINK STREAM (Hỗ trợ cả Playlist và bài lẻ)
                url2 = None
                title = "Unknown Title"

                # Nếu là Playlist, lấy bài đầu tiên
                if 'entries' in info:
                    print("📂 Phát hiện Playlist, đang chọn bài đầu tiên...")
                    entry = info['entries'][0]
                    # Nếu entry chưa có link stream, phải extract lại bài đó
                    if 'url' not in entry or 'formats' not in entry:
                        with yt_dlp.YoutubeDL(ytdl_opts) as ydl:
                            entry = ydl.extract_info(entry['url'], download=False)
                    url2 = entry.get('url')
                    title = entry.get('title')
                else:
                    # Nếu là bài đơn lẻ
                    url2 = info.get('url')
                    title = info.get('title')

                # Nếu vẫn chưa tìm thấy url2, tìm trong formats
                if not url2 and 'formats' in info:
                    url2 = info['formats'][0]['url']

                if url2:
                    source = discord.FFmpegOpusAudio(url2, **ffmpeg_opts, executable='ffmpeg')
                    vc.play(source)
                    print(f"🎵 Đã lên nhạc: {title}")
                else:
                    print("❌ Không tìm thấy link stream nhạc hợp lệ.")
                
            except Exception as e:
                print(f"Lỗi phát nhạc: {e}")

    # 2. TỰ ĐỘNG THOÁT KHI PHÒNG TRỐNG
    vc = member.guild.voice_client
    if vc and vc.channel:
        real_members = [m for m in vc.channel.members if not m.bot]
        if len(real_members) == 0:
            await vc.disconnect()
            print("🚪 Phòng trống, Bot đã rút lui.")

if TOKEN:
    bot.run(TOKEN)
else:
    print("❌ LỖI: Thiếu DISCORD_TOKEN trong Variables!")