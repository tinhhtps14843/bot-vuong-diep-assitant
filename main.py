import os
import discord
from discord.ext import commands
import yt_dlp
import asyncio

# --- CẤU HÌNH ---
TOKEN = os.getenv('DISCORD_TOKEN')
TARGET_VOICE_CHANNEL = 'Music' 
YOUTUBE_URL = 'https://youtu.be/HW93WQAjkts'

intents = discord.Intents.default()
intents.voice_states = True
intents.message_content = True
intents.members = True  # Quan trọng để kiểm tra số người trong phòng
bot = commands.Bot(command_prefix='!', intents=intents)


# Cấu hình yt-dlp mới để lách bộ lọc YouTube
ytdl_opts = {
    'format': 'bestaudio/best',
    'quiet': True,
    'noplaylist': True,
    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'nocheckcertificate': True,
    'ignoreerrors': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0' # Quan trọng cho server
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
    # 1. TỰ ĐỘNG VÀO VÀ PHÁT NHẠC KHI CÓ NGƯỜI VÀO
    if after.channel is not None and after.channel.name == TARGET_VOICE_CHANNEL and not member.bot:
        vc = member.guild.voice_client
        if vc is None:
            vc = await after.channel.connect()
        
        # Nếu đang không phát nhạc thì mới bắt đầu phát bài mới
        if not vc.is_playing():
            try:
                with yt_dlp.YoutubeDL(ytdl_opts) as ydl:
                    info = ydl.extract_info(YOUTUBE_URL, download=False)
                    url2 = info['url']
                    # Railway sẽ tự tìm lệnh ffmpeg nếu bạn đã thêm NIXPACKS_PKGS = ffmpeg
                    source = await discord.FFmpegOpusAudio.from_probe(url2, **ffmpeg_opts)
                    vc.play(source)
                    print(f"🎵 Đang quẩy nhạc chill phục vụ sếp {member.name}")
            except Exception as e:
                print(f"Lỗi khi phát nhạc: {e}")

    # 2. TỰ ĐỘNG THOÁT KHI PHÒNG KHÔNG CÒN AI (TRỪ BOT)
    vc = member.guild.voice_client
    if vc and vc.channel:
        # Lọc danh sách thành viên không phải là Bot
        real_members = [m for m in vc.channel.members if not m.bot]
        
        # Nếu danh sách người thật trống rỗng
        if len(real_members) == 0:
            await vc.disconnect()
            print(f"🚪 Không còn ai trong phòng {vc.channel.name}, Bot đã tự out!")

# Kiểm tra Token trước khi chạy
if TOKEN:
    bot.run(TOKEN)
else:
    print("❌ LỖI: Không tìm thấy DISCORD_TOKEN trong Variables của Railway!")