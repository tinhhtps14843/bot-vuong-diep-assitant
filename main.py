import os
import discord
from discord.ext import commands
import yt_dlp
import asyncio
import random # Thêm để xáo trộn nhạc

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

# Hàng đợi bài hát toàn cục
song_queue = []

ytdl_opts = {
    'format': 'bestaudio/best',
    'quiet': True,
    'noplaylist': False,
    'extract_flat': True, # CỰC QUAN TRỌNG: Để không bị tràn RAM khi nạp list dài
}

ffmpeg_opts = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn -b:a 64k -threads 1' # Bitrate thấp để ổn định trên Railway
}

def play_next(vc):
    """Hàm tự động bốc bài tiếp theo"""
    if len(song_queue) > 0:
        next_song = song_queue.pop(0)
        
        try:
            # Chỉ lấy link stream khi thực sự bắt đầu hát bài đó
            with yt_dlp.YoutubeDL({'format': 'bestaudio/best', 'quiet': True}) as ydl:
                info = ydl.extract_info(next_song['url'], download=False)
                url2 = info['url']
            
            source = discord.FFmpegOpusAudio(url2, **ffmpeg_opts)
            
            # Sử dụng bot.loop.call_soon_threadsafe để tránh lỗi xung đột luồng khi gọi play_next
            vc.play(source, after=lambda e: bot.loop.call_soon_threadsafe(play_next, vc))
            print(f"🎵 Đang phát: {next_song['title']}")
            
        except Exception as e:
            print(f"⚠️ Lỗi khi phát bài này, đang thử bài tiếp theo: {e}")
            play_next(vc)
    else:
        print("✅ Đã phát hết danh sách nhạc.")

@bot.event
async def on_ready():
    print(f'--- Vương Diệp Assistant Đã Sẵn Sàng ---')

@bot.event
async def on_voice_state_update(member, before, after):
    if after.channel is not None and after.channel.name == TARGET_VOICE_CHANNEL and not member.bot:
        vc = member.guild.voice_client
        if vc is None:
            try:
                vc = await after.channel.connect(timeout=60.0, reconnect=True)
                print(f"✅ Đã vào phòng: {after.channel.name}")
            except Exception as e:
                print(f"❌ Lỗi kết nối Voice: {e}")
                return
        
        # Nếu Bot đang rảnh và hàng đợi trống, tiến hành nạp danh sách
        if not vc.is_playing() and len(song_queue) == 0:
            try:
                loop = asyncio.get_event_loop()
                def fetch_info():
                    with yt_dlp.YoutubeDL(ytdl_opts) as ydl:
                        return ydl.extract_info(YOUTUBE_URL, download=False)

                print(f"⏳ Đang nạp danh sách: {YOUTUBE_URL}")
                info = await loop.run_in_executor(None, fetch_info)
                
                new_songs = []
                if 'entries' in info:
                    for entry in info['entries']:
                        new_songs.append({
                            'url': entry.get('url') or entry.get('webpage_url'),
                            'title': entry.get('title', 'Unknown Title')
                        })
                    
                    # --- NÂNG CẤP: XÁO TRỘN NHẠC ---
                    random.shuffle(new_songs)
                    song_queue.extend(new_songs)
                    print(f"📂 Đã nạp và xáo trộn {len(new_songs)} bài.")
                else:
                    song_queue.append({'url': info['url'], 'title': info['title']})

                if not vc.is_playing():
                    play_next(vc)
                
            except Exception as e:
                print(f"❌ Lỗi xử lý playlist: {e}")

    # 2. TỰ ĐỘNG THOÁT KHI PHÒNG TRỐNG
    vc = member.guild.voice_client
    if vc and vc.channel:
        real_members = [m for m in vc.channel.members if not m.bot]
        if len(real_members) == 0:
            song_queue.clear()
            if vc.is_playing():
                vc.stop()
            await vc.disconnect()
            print("🚪 Phòng trống, Bot đã rút lui.")

if TOKEN:
    bot.run(TOKEN)