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

# Hàng đợi bài hát toàn cục
song_queue = []

ytdl_opts = {
    'format': 'bestaudio/best',
    'quiet': True,
    'noplaylist': False, # Cho phép lấy toàn bộ danh sách
    'extract_flat': True, # Lấy thông tin nhanh, không extract link stream ngay lập tức
}

ffmpeg_opts = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn -b:a 64k -threads 1' 
}

def play_next(vc):
    """Hàm tự động phát bài tiếp theo trong hàng đợi"""
    if len(song_queue) > 0:
        next_song = song_queue.pop(0)
        
        # Vì dùng extract_flat: True nên giờ mới cần lấy link stream thực tế (url)
        with yt_dlp.YoutubeDL({'format': 'bestaudio/best', 'quiet': True}) as ydl:
            info = ydl.extract_info(next_song['url'], download=False)
            url2 = info['url']
        
        source = discord.FFmpegOpusAudio(url2, **ffmpeg_opts)
        # Tham số after sẽ gọi lại chính hàm này khi bài hát kết thúc
        vc.play(source, after=lambda e: play_next(vc))
        print(f"🎵 Đang phát: {next_song['title']}")
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
                
                if 'entries' in info:
                    # Nạp tất cả bài hát vào hàng đợi
                    for entry in info['entries']:
                        song_queue.append({
                            'url': entry.get('url') or entry.get('webpage_url'),
                            'title': entry.get('title', 'Unknown Title')
                        })
                    print(f"📂 Đã thêm {len(info['entries'])} bài vào hàng đợi.")
                else:
                    # Nếu chỉ là 1 bài đơn lẻ
                    song_queue.append({'url': info['url'], 'title': info['title']})

                # Bắt đầu phát bài đầu tiên
                play_next(vc)
                
            except Exception as e:
                print(f"❌ Lỗi xử lý playlist: {e}")

    # 2. TỰ ĐỘNG THOÁT KHI PHÒNG TRỐNG
    vc = member.guild.voice_client
    if vc and vc.channel:
        real_members = [m for m in vc.channel.members if not m.bot]
        if len(real_members) == 0:
            song_queue.clear() # Xóa sạch hàng đợi
            if vc.is_playing():
                vc.stop()
            await vc.disconnect()
            print("🚪 Phòng trống, Bot đã rút lui.")

if TOKEN:
    bot.run(TOKEN)