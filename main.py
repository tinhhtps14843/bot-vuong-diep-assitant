import os
import discord
from discord.ext import commands
import yt_dlp
import asyncio
import random

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

song_queue = []
current_song_url = None # Biến để theo dõi bài đang phát

ytdl_opts = {
    'format': 'bestaudio/best',
    'quiet': True,
    'noplaylist': False,
    'extract_flat': True,
}

ffmpeg_opts = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn -b:a 64k -threads 1' 
}

def play_next(vc):
    global current_song_url
    
    if len(song_queue) > 0:
        # Lấy bài đầu hàng đợi và XÓA LUÔN khỏi list
        next_song = song_queue.pop(0)
        current_song_url = next_song['url']
        
        try:
            with yt_dlp.YoutubeDL({'format': 'bestaudio/best', 'quiet': True}) as ydl:
                info = ydl.extract_info(next_song['url'], download=False)
                url2 = info['url']
            
            source = discord.FFmpegOpusAudio(url2, **ffmpeg_opts)
            
            # Sử dụng vòng lặp sự kiện của Bot để gọi play_next một cách sạch sẽ
            def handle_next(error):
                if error: print(f"Lỗi Player: {error}")
                # Ép Bot chạy play_next cho bài tiếp theo
                coro = asyncio.run_coroutine_threadsafe(delayed_next(vc), bot.loop)
                try:
                    coro.result()
                except:
                    pass

            vc.play(source, after=handle_next)
            print(f"🎵 Đang phát: {next_song['title']}")
            
        except Exception as e:
            print(f"⚠️ Lỗi bài này, nhảy bài tiếp: {e}")
            play_next(vc)
    else:
        print("✅ Đã phát hết danh sách.")

async def delayed_next(vc):
    """Tạo khoảng nghỉ ngắn giữa 2 bài để Discord kịp reset trạng thái"""
    await asyncio.sleep(1)
    if not vc.is_playing():
        play_next(vc)

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
            except Exception as e:
                print(f"❌ Lỗi: {e}")
                return
        
        if not vc.is_playing() and len(song_queue) == 0:
            try:
                loop = asyncio.get_event_loop()
                def fetch_info():
                    with yt_dlp.YoutubeDL(ytdl_opts) as ydl:
                        return ydl.extract_info(YOUTUBE_URL, download=False)

                info = await loop.run_in_executor(None, fetch_info)
                
                new_songs = []
                if 'entries' in info:
                    for entry in info['entries']:
                        url = entry.get('url') or entry.get('webpage_url')
                        if url:
                            new_songs.append({'url': url, 'title': entry.get('title', 'Nhạc không tên')})
                    
                    random.shuffle(new_songs)
                    song_queue.extend(new_songs)
                    print(f"📂 Nạp {len(new_songs)} bài.")
                else:
                    song_queue.append({'url': info['url'], 'title': info['title']})

                if not vc.is_playing():
                    play_next(vc)
                
            except Exception as e:
                print(f"❌ Lỗi playlist: {e}")

    # TỰ ĐỘNG THOÁT
    vc = member.guild.voice_client
    if vc and vc.channel:
        real_members = [m for m in vc.channel.members if not m.bot]
        if len(real_members) == 0:
            song_queue.clear()
            if vc.is_playing(): vc.stop()
            await vc.disconnect()

if TOKEN:
    bot.run(TOKEN)