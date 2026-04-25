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
bot = commands.Bot(command_prefix='!', intents=intents)

# Cấu hình yt-dlp và ffmpeg
ytdl_opts = {'format': 'bestaudio/best', 'quiet': True, 'noplaylist': True}
ffmpeg_opts = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

@bot.event
async def on_ready():
    print(f'Vương Diệp Assistant đã sẵn sàng tự hát!')

@bot.event
async def on_voice_state_update(member, before, after):
    # Khi có người vào kênh "Music"
    if after.channel is not None and after.channel.name == TARGET_VOICE_CHANNEL and not member.bot:
        vc = member.guild.voice_client
        if vc is None:
            vc = await after.channel.connect()
        
        # Nếu đang không phát gì thì bắt đầu phát
        if not vc.is_playing():
            with yt_dlp.YoutubeDL(ytdl_opts) as ydl:
                info = ydl.extract_info(YOUTUBE_URL, download=False)
                url2 = info['url']
                # Gọi trực tiếp ffmpeg.exe trong cùng thư mục
                source = await discord.FFmpegOpusAudio.from_probe(url2, **ffmpeg_opts)
                vc.play(source)
                print(f"🎵 Đang quẩy nhạc chill cho sếp {member.name}")

bot.run(TOKEN)