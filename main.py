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

# Bắt buộc phải bật message_content để Bot đọc được lệnh sếp gõ
intents = discord.Intents.default()
intents.voice_states = True
intents.message_content = True
intents.members = True 

# Đặt Prefix là dấu chấm câu thích hợp (Ví dụ: !play, !skip)
bot = commands.Bot(command_prefix='!', intents=intents)

song_queue = []
current_song = None # Lưu thông tin bài đang phát để dùng cho lệnh !nowplaying

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
    global current_song
    
    if len(song_queue) > 0:
        next_song = song_queue.pop(0)
        current_song = next_song # Cập nhật bài đang phát
        
        try:
            with yt_dlp.YoutubeDL({'format': 'bestaudio/best', 'quiet': True}) as ydl:
                info = ydl.extract_info(next_song['url'], download=False)
                url2 = info['url']
            
            source = discord.FFmpegOpusAudio(url2, **ffmpeg_opts)
            
            def handle_next(error):
                if error: print(f"Lỗi Player: {error}")
                coro = asyncio.run_coroutine_threadsafe(delayed_next(vc), bot.loop)
                try: coro.result()
                except: pass

            vc.play(source, after=handle_next)
            print(f"🎵 Đang phát: {next_song['title']}")
            
        except Exception as e:
            print(f"⚠️ Lỗi bài này, nhảy bài tiếp: {e}")
            play_next(vc)
    else:
        current_song = None
        print("✅ Đã phát hết danh sách.")

async def delayed_next(vc):
    await asyncio.sleep(1)
    if vc and not vc.is_playing() and not vc.is_paused():
        play_next(vc)

@bot.event
async def on_ready():
    print(f'--- Vương Diệp Assistant Đã Sẵn Sàng Với Lệnh Điều Khiển ---')

@bot.event
async def on_voice_state_update(member, before, after):
    # Logic tự động vào phòng khi sếp vào kênh 'Music'
    if after.channel is not None and after.channel.name == TARGET_VOICE_CHANNEL and not member.bot:
        vc = member.guild.voice_client
        if vc is None:
            try:
                vc = await after.channel.connect(timeout=60.0, reconnect=True)
                print(f"✅ Đã vào phòng: {after.channel.name}")
            except Exception as e:
                print(f"❌ Lỗi kết nối Voice: {e}")
                return
        
        if not vc.is_playing() and not vc.is_paused() and len(song_queue) == 0:
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
                    print(f"📂 Nạp và xáo trộn {len(new_songs)} bài.")
                else:
                    song_queue.append({'url': info['url'], 'title': info['title']})

                if not vc.is_playing():
                    play_next(vc)
                
            except Exception as e:
                print(f"❌ Lỗi playlist: {e}")

    # TỰ ĐỘNG THOÁT KHI PHÒNG TRỐNG
    vc = member.guild.voice_client
    if vc and vc.channel:
        real_members = [m for m in vc.channel.members if not m.bot]
        if len(real_members) == 0:
            global song_queue, current_song
            song_queue.clear()
            current_song = None
            if vc.is_playing(): vc.stop()
            await vc.disconnect()
            print("🚪 Phòng trống, Bot đã rút lui.")

# --- CÁC CÂU LỆNH ĐIỀU KHIỂN (COMMANDS) ---

@bot.command(name='skip')
async def skip(ctx):
    """Bỏ qua bài hiện tại"""
    vc = ctx.voice_client
    if vc and (vc.is_playing() or vc.is_paused()):
        vc.stop() # Lệnh stop sẽ tự kích hoạt after=handle_next để nhảy bài mới
        await ctx.send("⏭️ **Đã bỏ qua bài hiện tại theo lệnh sếp!**")
    else:
        await ctx.send("❌ Hiện tại đang không có nhạc nào phát để skip sếp ơi.")

@bot.command(name='pause')
async def pause(ctx):
    """Tạm dừng nhạc"""
    vc = ctx.voice_client
    if vc and vc.is_playing():
        vc.pause()
        await ctx.send("⏸️ **Đã tạm dừng nhạc.**")
    else:
        await ctx.send("❌ Nhạc đang không phát hoặc đã dừng sẵn rồi sếp.")

@bot.command(name='resume')
async def resume(ctx):
    """Tiếp tục phát nhạc"""
    vc = ctx.voice_client
    if vc and vc.is_paused():
        vc.resume()
        await ctx.send("▶️ **Tiếp tục quẩy nhạc nào sếp!**")
    else:
        await ctx.send("❌ Nhạc có bị pause đâu mà phát tiếp sếp ơi.")

@bot.command(name='np')
async def now_playing(ctx):
    """Xem tên bài hát đang phát"""
    if current_song:
        await ctx.send(f"🎵 **Đang phát:** `{current_song['title']}`\n📜 **Còn lại trong hàng đợi:** {len(song_queue)} bài.")
    else:
        await ctx.send("📭 Hiện tại không có bài nào đang phát.")

if TOKEN:
    bot.run(TOKEN)