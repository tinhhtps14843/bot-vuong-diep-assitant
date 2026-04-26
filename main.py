import os
import discord
from discord.ext import commands
import yt_dlp
import asyncio

# --- CẤU HÌNH ---
TOKEN = os.getenv('DISCORD_TOKEN')
TARGET_VOICE_CHANNEL = 'Music' 

# Lấy URL từ biến môi trường YOUTUBE_URL trên Railway
# Nếu không có biến trên Railway, nó sẽ dùng link mặc định này
DEFAULT_URL = 'https://www.youtube.com/watch?v=jfKfPfyJRdk'
YOUTUBE_URL = os.getenv('YOUTUBE_URL', DEFAULT_URL)

intents = discord.Intents.default()
intents.voice_states = True
intents.message_content = True
intents.members = True 
bot = commands.Bot(command_prefix='!', intents=intents)

# Cấu hình yt-dlp
ytdl_opts = {
    'format': 'bestaudio/best',
    'quiet': True,
    'noplaylist': True,
    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
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
                # Đợi tối đa 30s để handshake
                vc = await after.channel.connect(timeout=30.0, reconnect=True)
            except Exception as e:
                print(f"Lỗi kết nối Voice: {e}")
                return
        
        if not vc.is_playing():
            try:
                loop = asyncio.get_event_loop()
                
                def fetch_info():
                    # Thêm các tùy chọn an toàn hơn để tránh NoneType
                    with yt_dlp.YoutubeDL(ytdl_opts) as ydl:
                        return ydl.extract_info(YOUTUBE_URL, download=False)

                print(f"⏳ Đang xử lý link: {YOUTUBE_URL}")
                info = await loop.run_in_executor(None, fetch_info)
                
                if info is None:
                    print("❌ Lỗi: Không thể lấy thông tin từ URL này (YouTube chặn IP).")
                    return

                # Cách lấy URL thông minh: Thử nhiều cách để tránh lỗi NoneType
                url2 = None
                if 'url' in info:
                    url2 = info['url']
                elif 'formats' in info and len(info['formats']) > 0:
                    url2 = info['formats'][0]['url']

                if url2:
                    source = discord.FFmpegOpusAudio(url2, **ffmpeg_opts, executable='ffmpeg')
                    vc.play(source)
                    print(f"🎵 Đã lên nhạc: {info.get('title', 'Unknown Title')}")
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