import os
import discord
from discord.ext import commands
import yt_dlp
import asyncio

# --- CẤU HÌNH ---
TOKEN = os.getenv('DISCORD_TOKEN')
TARGET_VOICE_CHANNEL = 'Music' 
YOUTUBE_URL = 'https://soundcloud.com/discover/sets/personalized-tracks::trung-t-nh-h-768344095:1384474006?si=0e2c408339ad4651a2c74d06bbc6aab8&utm_source=clipboard&utm_medium=text&utm_campaign=social_sharing' # Thử link Lofi này để tránh bị chặn IP

intents = discord.Intents.default()
intents.voice_states = True
intents.message_content = True
intents.members = True 
bot = commands.Bot(command_prefix='!', intents=intents)

# Cấu hình yt-dlp mới (không dùng cookies, giả lập trình duyệt)
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
            vc = await after.channel.connect()
        
        if not vc.is_playing():
            try:
                # Dùng yt-dlp lấy link trực tiếp
                with yt_dlp.YoutubeDL(ytdl_opts) as ydl:
                    info = ydl.extract_info(YOUTUBE_URL, download=False)
                    url2 = info['url']
                    
                    # QUAN TRỌNG: Chỉ dùng 'ffmpeg', KHÔNG dùng 'ffmpeg.exe'
                    # Hệ thống Linux của Railway sẽ tự hiểu lệnh này
                    source = discord.FFmpegOpusAudio(url2, **ffmpeg_opts, executable='ffmpeg')
                    vc.play(source)
                    print(f"🎵 Đang phát nhạc cho: {member.name}")
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
    print("❌ Thiếu DISCORD_TOKEN!")