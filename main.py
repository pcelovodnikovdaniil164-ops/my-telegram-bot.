import asyncio
import os
import random
import warnings
import requests
from PIL import Image
import google.generativeai as genai
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command, CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
import yt_dlp
from aiohttp import web

# Отключаем предупреждения
warnings.filterwarnings("ignore")

# --- КОНФИГУРАЦИЯ ---
TOKEN = "8171123432:AAE3oBJMtRBiryyJPrODcvZLqSo3qOLY1Cs"
ADMIN_ID = 6557367300
GEMINI_KEY = "AQ.Ab8RN6Lq9dKAY279ar8rVhuQCThmVZGp2L61XRDFUxzyOZqGlQ"

genai.configure(api_key=GEMINI_KEY)
gemini_model = genai.GenerativeModel("gemini-1.5-flash")

bot = Bot(token=TOKEN)
dp = Dispatcher()

ACTIVE_USERS = set()
USER_FAVORITES = {}

IMAGE_URL = "https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExM3Z2azk2Y3R6Zmh0M3EydnA1Zjlpa2dweXljd3YyZjZidnhreHZxOSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/3o7abKba90aA2H4Z2M/giphy.gif"

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---
def search_youtube_tracks(query, max_results=4):
    ydl_opts = {'quiet': True, 'extract_flat': True, 'skip_download': True}
    results = []
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch{max_results}:{query}", download=False)
            if info and 'entries' in info:
                for entry in info['entries']:
                    video_id = entry.get('id')
                    if video_id:
                        results.append({'id': video_id, 'title': entry.get('title', 'Без названия')[:35]})
    except Exception:
        pass
    return results

def download_audio_by_id(video_id_or_url):
    if video_id_or_url.startswith("http"):
        url = video_id_or_url
        out_tmpl = 'song_link_%(id)s.%(ext)s'
    else:
        url = f"https://www.youtube.com/watch?v={video_id_or_url}"
        out_tmpl = f'song_{video_id_or_url}.%(ext)s'

    ydl_opts = {
        'format': 'bestaudio/best', 'outtmpl': out_tmpl, 'quiet': True,
        'nocheckcertificate': True, 'ignoreerrors': True,
        'extractor_args': {'youtube': {'player_client': ['android', 'web']}}
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return ydl.prepare_filename(info), info.get('title', 'Трек')

def recognize_audio_file(file_path):
    try:
        with open(file_path, 'rb') as f:
            result = requests.post("https://api.audd.io/", data={'api_token': 'test', 'return': 'apple_music,spotify'}, files={'file': f}).json()
            if result.get('status') == 'success' and result.get('result'):
                return f"{result['result']['artist']} - {result['result']['title']}"
    except Exception:
        pass
    return None

# --- КЛАВИАТУРЫ ---
def get_main_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔎 Поиск трека", callback_data="btn_search_music"), InlineKeyboardButton(text="📥 Скачать", callback_data="btn_download_link")],
        [InlineKeyboardButton(text="📸 Поиск по фото", callback_data="btn_screenshot_info"), InlineKeyboardButton(text="🎙️ Shazam", callback_data="btn_shazam_info")],
        [InlineKeyboardButton(text="🔥 Чарт недели", callback_data="btn_top_chart"), InlineKeyboardButton(text="🎲 Рандом трек", callback_data="btn_random_track")],
        [InlineKeyboardButton(text="🎧 Вайб плейлисты", callback_data="btn_vibe_playlist"), InlineKeyboardButton(text="📜 Текст песни", callback_data="btn_lyrics_info")],
        [InlineKeyboardButton(text="🎱 Шар судьбы", callback_data="btn_magic_8ball"), InlineKeyboardButton(text="🗿 Мем дня", callback_data="btn_meme_day")],
        [InlineKeyboardButton(text="☀️ Прогноз погоды", callback_data="btn_weather_info"), InlineKeyboardButton(text="⭐ Моё Избранное", callback_data="btn_favorites")]
    ])

# --- СТАРТ И МЕНЮ ---
@dp.message(CommandStart())
@dp.message(Command("menu"))
async def send_menu(message: types.Message):
    ACTIVE_USERS.add(message.from_user.id)
    text = (
        f"🎧 **Welcome to Music Space, {message.from_user.first_name}!** 🎧\n"
        "⚡️ ═════════════════════ ⚡️\n\n"
        "🤖 **Твой персональный умный медиа-комбайн!**\n\n"
        "👇 *Выбери нужный раздел на панели управления ниже или отправь название/скриншот:*"
    )
    try:
        await message.answer_animation(animation=IMAGE_URL, caption=text, reply_markup=get_main_keyboard(), parse_mode="Markdown")
    except Exception:
        await message.answer(text, reply_markup=get_main_keyboard(), parse_mode="Markdown")

# --- 5 АДМИН-ФИЧ ---
@dp.message(Command("admin"))
async def cmd_admin(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Статистика", callback_data="adm_stats"), InlineKeyboardButton(text="👥 Юзеры", callback_data="adm_users")],
        [InlineKeyboardButton(text="📢 Рассылка", callback_data="adm_broadcast")]
    ])
    await message.answer("🛠 **Панель Администратора:**", parse_mode="Markdown", reply_markup=kb)

@dp.message(Command("stats"))
async def cmd_stats(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer(f"📊 **Статистика:**\n👥 Уникальных пользователей: `{len(ACTIVE_USERS)}`", parse_mode="Markdown")

@dp.message(Command("users"))
async def cmd_users(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    if not ACTIVE_USERS:
        await message.answer("📁 База пользователей пуста.")
        return
    users_str = "\n".join([f"• `{uid}`" for uid in ACTIVE_USERS])
    await message.answer(f"👥 **Список пользователей:**\n\n{users_str}", parse_mode="Markdown")

@dp.message(Command("broadcast"))
async def cmd_broadcast(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    broadcast_text = "🔥 **Бот успешно обновлен и работает стабильно!** 🚀\n\n👇 Жми /menu и оцени работу!"
    success, fail = 0, 0
    status = await message.answer("📢 Рассылка запущена...")
    for uid in ACTIVE_USERS:
        try:
            await bot.send_message(uid, broadcast_text, parse_mode="Markdown", reply_markup=get_main_keyboard())
            success += 1
            await asyncio.sleep(0.05)
        except Exception:
            fail += 1
    await status.edit_text(f"✅ **Рассылка завершена!**\nУспешно: `{success}`\nОшибок: `{fail}`", parse_mode="Markdown")

@dp.callback_query(F.data.startswith("adm_"))
async def admin_callbacks(cb: types.CallbackQuery):
    if cb.from_user.id != ADMIN_ID:
        await cb.answer("⛔️ Нет доступа!", show_alert=True)
        return
    if cb.data == "adm_stats":
        await cb.message.answer(f"📊 В базе `{len(ACTIVE_USERS)}` пользователей.")
    elif cb.data == "adm_users":
        users_str = "\n".join([f"• `{uid}`" for uid in ACTIVE_USERS]) if ACTIVE_USERS else "Пусто"
        await cb.message.answer(f"👥 **Юзеры:**\n{users_str}", parse_mode="Markdown")
    elif cb.data == "adm_broadcast":
        await cb.message.answer("📢 Отправь команду `/broadcast` в чат для запуска рассылки.")
    await cb.answer()

# --- ИНЛАЙН ИНСТРУМЕНТЫ ---
@dp.callback_query(F.data == "btn_magic_8ball")
async def cb_magic_8ball(cb: types.CallbackQuery):
    await cb.answer()
    res = random.choice(["Бесспорно! 🎯", "Мне кажется — да. 👍", "Пока не ясно. 🎲", "Мой ответ — НЕТ. 🛑", "Знаки говорят — ДА! ✨"])
    await cb.message.answer(f"🎱 **Шар судьбы:**\n\n_{res}_", parse_mode="Markdown")

@dp.callback_query(F.data == "btn_meme_day")
async def cb_meme_day(cb: types.CallbackQuery):
    await cb.answer()
    await cb.message.answer_photo(photo=random.choice(["https://i.imgflip.com/1bij.jpg", "https://i.imgflip.com/26am.jpg"]), caption="🗿 **Мем дня!**")

@dp.callback_query(F.data == "btn_weather_info")
async def cb_weather_info(cb: types.CallbackQuery):
    await cb.answer()
    await cb.message.answer("☀️ Напиши в чат `Погода` и название города (например: `Погода Москва`)", parse_mode="Markdown")

@dp.callback_query(F.data == "btn_vibe_playlist")
async def cb_vibe_playlist(cb: types.CallbackQuery):
    await cb.answer()
    await cb.message.answer("🎧 **Вайб плейлисты:**\n• Фонк / Дрилл\n• Чилл / Лоу-фай", parse_mode="Markdown")

@dp.callback_query(F.data == "btn_lyrics_info")
async def cb_lyrics_info(cb: types.CallbackQuery):
    await cb.answer()
    await cb.message.answer("📜 Напиши `Текст` и название песни.", parse_mode="Markdown")

@dp.callback_query(F.data == "btn_favorites")
async def cb_favorites(cb: types.CallbackQuery):
    await cb.answer()
    favs = USER_FAVORITES.get(cb.from_user.id, [])
    await cb.message.answer(f"⭐ **Избранное:**\n\n" + ("\n".join([f"🎵 {t}" for t in favs]) if favs else "Пусто."), parse_mode="Markdown")

@dp.callback_query(F.data == "btn_download_link")
async def cb_download_link(cb: types.CallbackQuery):
    await cb.answer()
    await cb.message.answer("📥 Отправь ссылку на трек в чат.", parse_mode="Markdown")

@dp.callback_query(F.data == "btn_top_chart")
async def cb_top_chart(cb: types.CallbackQuery):
    await cb.answer()
    buttons = [[InlineKeyboardButton(text=f"🔥 {a}", callback_data=f"search_{a}")] for a in ["Miyagi & Эндшпиль", "MACAN", "Xcho"]]
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="btn_back_to_menu")])
    await cb.message.answer("🔥 **Чарт недели:**", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="Markdown")

@dp.callback_query(F.data == "btn_random_track")
async def cb_random_track(cb: types.CallbackQuery):
    await cb.answer()
    chosen = random.choice(["Miyagi", "KIZARU", "Skryptonite", "MACAN"])
    status_msg = await cb.message.answer(f"🎲 Ищу трек от **{chosen}**...")
    results = await asyncio.get_event_loop().run_in_executor(None, search_youtube_tracks, chosen)
    if results:
        buttons = [[InlineKeyboardButton(text=f"🎵 {t['title']}", callback_data=f"dl_{t['id']}"), InlineKeyboardButton(text="⭐", callback_data=f"fav_{t['id']}")] for t in results]
        await status_msg.edit_text(f"🎲 **Случайные треки ({chosen}):**", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="Markdown")
    else:
        await status_msg.edit_text("❌ Ничего не найдено.")

@dp.callback_query(F.data.startswith("search_"))
async def cb_search_from_chart(cb: types.CallbackQuery):
    await cb.answer()
    query = cb.data.replace("search_", "")
    status_msg = await cb.message.answer(f"⚡️ Ищу **{query}**...")
    results = await asyncio.get_event_loop().run_in_executor(None, search_youtube_tracks, query)
    if results:
        buttons = [[InlineKeyboardButton(text=f"🎵 {t['title']}", callback_data=f"dl_{t['id']}"), InlineKeyboardButton(text="⭐", callback_data=f"fav_{t['id']}")] for t in results]
        await status_msg.edit_text(f"🎯 **Результаты:**", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="Markdown")
    else:
        await status_msg.edit_text("❌ Не найдено.")

@dp.callback_query(F.data == "btn_back_to_menu")
async def cb_back_to_menu(cb: types.CallbackQuery):
    await cb.answer()
    await cb.message.answer("👇 **Главное меню:**", reply_markup=get_main_keyboard(), parse_mode="Markdown")

@dp.callback_query(F.data == "btn_search_music")
async def cb_search_music(cb: types.CallbackQuery):
    await cb.answer()
    await cb.message.answer("🔎 Напиши название песни в чат.", parse_mode="Markdown")

@dp.callback_query(F.data == "btn_screenshot_info")
async def cb_screenshot_info(cb: types.CallbackQuery):
    await cb.answer()
    await cb.message.answer("📸 Отправь скриншот обложки.", parse_mode="Markdown")

@dp.callback_query(F.data == "btn_shazam_info")
async def cb_shazam_info(cb: types.CallbackQuery):
    await cb.answer()
    await cb.message.answer("🎙️ Скинь голосовое сообщение или аудио.", parse_mode="Markdown")

@dp.callback_query(F.data.startswith("fav_"))
async def cb_add_favorite(cb: types.CallbackQuery):
    track_id = cb.data.replace("fav_", "")
    USER_FAVORITES.setdefault(cb.from_user.id, []).append(f"Трек ID: {track_id}")
    await cb.answer("⭐ Добавлено в избранное!", show_alert=True)

@dp.callback_query(F.data.startswith("dl_"))
async def cb_download_selected(cb: types.CallbackQuery):
    await cb.answer()
    status = await cb.message.answer("🚀 Загружаю аудио...")
    try:
        file_path, title = await asyncio.get_event_loop().run_in_executor(None, download_audio_by_id, cb.data.replace("dl_", ""))
        await cb.message.answer_audio(audio=types.FSInputFile(file_path), caption=f"🎶 **{title}**", parse_mode="Markdown")
        await status.delete()
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception:
        await status.edit_text("❌ Ошибка при скачивании трека.")

# --- ОБРАБОТКА ТЕКСТА (ПОГОДА, ТЕКСТЫ, ПОИСК) ---
@dp.message(F.text & ~F.text.startswith("/"))
async def process_text_input(message: types.Message):
    ACTIVE_USERS.add(message.from_user.id)
    query = message.text.strip()
    
    if query.lower().startswith("погода"):
        city = query[6:].strip() or "Москва"
        try:
            weather_data = requests.get(f'https://wttr.in/{city}?format=%C+%t+%w', timeout=5).text
            await message.answer(f"☀️ **Погода в {city}:**\n{weather_data}")
        except Exception:
            await message.answer("❌ Не удалось получить погоду.")
        return

    if query.lower().startswith("текст"):
        song = query[5:].strip()
        status = await message.answer(f"🔍 Ищу текст **{song}**...")
        try:
            resp = await asyncio.get_event_loop().run_in_executor(None, lambda: gemini_model.generate_content(f"Напиши текст песни {song}"))
            await status.edit_text(f"📜 **Текст песни:**\n\n{resp.text[:3800]}")
        except Exception:
            await status.edit_text("❌ Ошибка генерации текста.")
        return

    if query.startswith("http"):
        status = await message.answer("🚀 Качаю трек по ссылке...")
        try:
            file_path, title = await asyncio.get_event_loop().run_in_executor(None, download_audio_by_id, query)
            await message.answer_audio(audio=types.FSInputFile(file_path), caption=f"🎶 **{title}**", parse_mode="Markdown")
            await status.delete()
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception:
            await status.edit_text("❌ Ошибка скачивания по ссылке.")
        return

    status = await message.answer(f"⚡️ Поиск: **{query}**...", parse_mode="Markdown")
    results = await asyncio.get_event_loop().run_in_executor(None, search_youtube_tracks, query)
    if not results:
        await status.edit_text("❌ Ничего не найдено.")
        return
    buttons = [[InlineKeyboardButton(text=f"🎵 {t['title']}", callback_data=f"dl_{t['id']}"), InlineKeyboardButton(text="⭐", callback_data=f"fav_{t['id']}")] for t in results]
    await status.edit_text("🎯 **Выбери нужный трек:**", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="Markdown")

# --- РАСПОЗНАВАНИЕ ФОТО ---
@dp.message(F.photo)
async def handle_photo_search(message: types.Message):
    ACTIVE_USERS.add(message.from_user.id)
    status = await message.answer("👁️ Анализирую скриншот...")
    temp_img = f"temp_{message.photo[-1].file_id}.jpg"
    try:
        file = await bot.get_file(message.photo[-1].file_id)
        await bot.download_file(file.file_path, temp_img)
        resp = await asyncio.get_event_loop().run_in_executor(None, lambda: gemini_model.generate_content(["Ответь ТОЛЬКО в формате: Исполнитель - Название. Или 'NOT_FOUND'", Image.open(temp_img)]))
        txt = resp.text.strip()
        if os.path.exists(temp_img):
            os.remove(temp_img)
        
        if "NOT_FOUND" in txt:
            await status.edit_text("❌ Трек по фото не распознан.")
            return
            
        await status.edit_text(f"🎯 **Нашел:** `{txt}`\nИщу аудио...", parse_mode="Markdown")
        results = await asyncio.get_event_loop().run_in_executor(None, search_youtube_tracks, txt)
        if results:
            buttons = [[InlineKeyboardButton(text=f"🎵 {t['title']}", callback_data=f"dl_{t['id']}"), InlineKeyboardButton(text="⭐", callback_data=f"fav_{t['id']}")] for t in results]
            await status.edit_text(f"🎶 **Результаты ({txt}):**", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="Markdown")
        else:
            await status.edit_text("❌ Не удалось найти аудио для скачивания.")
    except Exception:
        if os.path.exists(temp_img):
            os.remove(temp_img)
        await status.edit_text("❌ Ошибка при обработке фото.")

# --- РАСПОЗНАВАНИЕ АУДИО (SHAZAM) ---
@dp.message(F.voice | F.video_note | F.audio | F.video)
async def handle_media(message: types.Message):
    ACTIVE_USERS.add(message.from_user.id)
    file_id = message.voice.file_id if message.voice else message.video_note.file_id if message.video_note else message.audio.file_id if message.audio else message.video.file_id
    status = await message.answer("🎧 **Слушаю аудио...**", parse_mode="Markdown")
    temp_file = f"sample_{message.from_user.id}.ogg"
    try:
        file = await bot.get_file(file_id)
        await bot.download_file(file.file_path, temp_file)
        track_name = await asyncio.get_event_loop().run_in_executor(None, recognize_audio_file, temp_file)
        if os.path.exists(temp_file):
            os.remove(temp_file)
            
        if not track_name:
            await status.edit_text("❌ Не удалось распознать мелодию.")
            return
            
        status = await status.edit_text(f"🔍 **Распознано:** {track_name}\nИщу в базе...", parse_mode="Markdown")
        results = await asyncio.get_event_loop().run_in_executor(None, search_youtube_tracks, track_name)
        if results:
            buttons = [[InlineKeyboardButton(text=f"🎵 {t['title']}", callback_data=f"dl_{t['id']}"), InlineKeyboardButton(text="⭐", callback_data=f"fav_{t['id']}")] for t in results]
            await status.edit_text(f"🎶 **Распознано:** {track_name}", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="Markdown")
        else:
            await status.edit_text(f"❌ Нашел «{track_name}», но скачать не получилось.")
    except Exception:
        if os.path.exists(temp_file):
            os.remove(temp_file)
        await status.edit_text("❌ Ошибка при распознавании аудио.")

# --- СЕРВЕР ДЛЯ RENDER ---
async def handle_ping(request):
    return web.Response(text="Bot is running!")

async def main():
    app = web.Application()
    app.router.add_get('/', handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

    print("🚀 Бот успешно запущен и готов к работе!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
