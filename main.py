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

# Отключаем выводы предупреждений в консоль
warnings.filterwarnings("ignore")

TOKEN = "8171123432:AAE3oBJMtRBiryyJPrODcvZLqSo3qOLY1Cs"
ADMIN_ID = 6557367300

# Новая сочная GIF-анимация для главного меню (Music Wave / Cyberpunk Vibe)
IMAGE_URL = "https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExM3Z2azk2Y3R6Zmh0M3EydnA1Zjlpa2dweXljd3YyZjZidnhreHZxOSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/3o7abKba90aA2H4Z2M/giphy.gif"

# --- НАСТРОЙКА GEMINI API ---
GEMINI_KEY = "AQ.Ab8RN6Lq9dKAY279ar8rVhuQCThmVZGp2L61XRDFUxzyOZqGlQ"
genai.configure(api_key=GEMINI_KEY)
gemini_model = genai.GenerativeModel("gemini-1.5-flash")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Временное хранилище избранного треков в памяти
USER_FAVORITES = {}

# Хелпер для логов
def log_action(user: types.User, action_text: str):
    username = f"@{user.username}" if user.username else "нет_юзернейма"
    info = f"👤 [{user.first_name} | {username} | ID: {user.id}] ➔ {action_text}"
    print(info)
    try:
        with open("logs.txt", "a", encoding="utf-8") as f:
            f.write(f"{info}\n")
    except Exception as e:
        print(f"Ошибка записи лога: {e}")

# --- 1. БЫСТРЫЙ ПОИСК ВАРИАНТОВ ---
def search_youtube_tracks(query, max_results=4):
    ydl_opts = {
        'quiet': True,
        'extract_flat': True,
        'skip_download': True,
    }
    results = []
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch{max_results}:{query}", download=False)
            if info and 'entries' in info:
                for entry in info['entries']:
                    title = entry.get('title', 'Без названия')
                    video_id = entry.get('id')
                    if video_id:
                        results.append({'id': video_id, 'title': title[:35]})
    except Exception as e:
        print(f"Ошибка поиска: {e}")
    return results

# --- 2. СКАЧИВАНИЕ ТРЕКА ПО ID ИЛИ ССЫЛКЕ ---
def download_audio_by_id(video_id_or_url):
    if video_id_or_url.startswith("http://") or video_id_or_url.startswith("https://"):
        url = video_id_or_url
        out_tmpl = 'song_link_%(id)s.%(ext)s'
    else:
        url = f"https://www.youtube.com/watch?v={video_id_or_url}"
        out_tmpl = f'song_{video_id_or_url}.%(ext)s'

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': out_tmpl,
        'quiet': True,
        'nocheckcertificate': True,
        'ignoreerrors': True,
        'extractor_args': {'youtube': {'player_client': ['android', 'web']}}
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        title = info.get('title', 'Трек')
        return filename, title

# --- 3. РАСПОЗНАВАНИЕ ТРЕКА (AudD) ---
def recognize_audio_file(file_path):
    try:
        url = "https://api.audd.io/"
        data = {'api_token': 'test', 'return': 'apple_music,spotify'}
        files = {'file': open(file_path, 'rb')}
        result = requests.post(url, data=data, files=files).json()
        if result.get('status') == 'success' and result.get('result'):
            artist = result['result']['artist']
            title = result['result']['title']
            return f"{artist} - {title}"
    except Exception:
        pass
    return None

# --- 4. КРАСИВОЕ МЕНЮ КНОПОК ---
def get_main_keyboard():
    keyboard = [
        [InlineKeyboardButton(text="🔎 Поиск трека", callback_data="btn_search_music"),
         InlineKeyboardButton(text="📥 Скачать по ссылке", callback_data="btn_download_link")],
        [InlineKeyboardButton(text="📸 Поиск по фото", callback_data="btn_screenshot_info"),
         InlineKeyboardButton(text="🎙️ Shazam (Аудио)", callback_data="btn_shazam_info")],
        [InlineKeyboardButton(text="🔥 Чарт недели", callback_data="btn_top_chart"),
         InlineKeyboardButton(text="🎲 Рандом трек", callback_data="btn_random_track")],
        [InlineKeyboardButton(text="🎧 Вайб плейлисты", callback_data="btn_vibe_playlist"),
         InlineKeyboardButton(text="📜 Текст песни", callback_data="btn_lyrics_info")],
        [InlineKeyboardButton(text="🎱 Шар судьбы", callback_data="btn_magic_8ball"),
         InlineKeyboardButton(text="🗿 Мем дня", callback_data="btn_meme_day")],
        [InlineKeyboardButton(text="☀️ Прогноз погоды", callback_data="btn_weather_info"),
         InlineKeyboardButton(text="⭐ Моё Избранное", callback_data="btn_favorites")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# --- 5. СТАРТ И МЕНЮ ---
@dp.message(CommandStart())
@dp.message(Command("menu"))
async def send_menu(message: types.Message):
    log_action(message.from_user, "🟢 Запустил бота / вызвал /menu")

    welcome_text = (
        f"🎧 **Welcome to Music Space, {message.from_user.first_name}!** 🎧\n"
        "⚡️ ═════════════════════ ⚡️\n\n"
        "🤖 **Твой персональный умный медиа-комбайн!**\n\n"
        "🔥 **Главные фичи:**\n"
        " ├ 🎵 **Поиск & Загрузка:** Название, ссылки (YT/VK/Yandex)\n"
        " ├ 📸 **Умный глаз:** Распознавание трека по скриншоту\n"
        " ├ 🎙️ **Shazam:** Сканирование голосовых и видео-клипов\n"
        " ├ 🎧 **Вайб & Чарты:** Подборки под настроение\n"
        " ├ 📜 **Lyrics AI:** Тексты любых треков\n"
        " └ 🎱 **Развлечения:** Шар предсказаний, Мемы, Погода\n\n"
        "👇 *Выбери нужный раздел на панели управления ниже или отправь название/скриншот:* "
    )

    try:
        await message.answer_animation(
            animation=IMAGE_URL,
            caption=welcome_text,
            reply_markup=get_main_keyboard(),
            parse_mode="Markdown"
        )
    except Exception:
        await message.answer(welcome_text, reply_markup=get_main_keyboard(), parse_mode="Markdown")

# --- 6. АДМИН-КОМАНДЫ ---

@dp.message(Command("logs"))
async def get_logs_file(message: types.Message):
    log_action(message.from_user, "⚙️ Попытка получить файл логов (/logs)")
    if message.from_user.id == ADMIN_ID:
        if os.path.exists("logs.txt"):
            file = types.FSInputFile("logs.txt")
            await message.answer_document(file, caption="📋 **Актуальный файл логов**", parse_mode="Markdown")
        else:
            await message.answer("Файл `logs.txt` пока пуст.")
    else:
        await message.answer("❌ У тебя нет прав для выполнения этой команды.")

@dp.message(Command("stats"))
async def show_stats(message: types.Message):
    log_action(message.from_user, "📊 Попытка посмотреть статистику (/stats)")
    if message.from_user.id == ADMIN_ID:
        if not os.path.exists("logs.txt"):
            await message.answer("Статистика пуста.")
            return

        user_ids = set()
        with open("logs.txt", "r", encoding="utf-8") as f:
            for line in f:
                if "ID:" in line:
                    try:
                        uid = int(line.split("ID:")[1].split("]")[0].strip())
                        user_ids.add(uid)
                    except Exception:
                        pass

        await message.answer(f"📊 **Статистика бота:**\n\n👤 Уникальных пользователей: **{len(user_ids)}**", parse_mode="Markdown")

@dp.message(Command("broadcast"))
async def broadcast_message(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    text_to_send = message.text.replace("/broadcast", "").strip()
    if not text_to_send:
        await message.answer("⚠️ Напиши текст рассылки после команды!\nПример: `/broadcast Вышло обновление бота!`", parse_mode="Markdown")
        return

    log_action(message.from_user, f"📢 Запустил рассылку: {text_to_send}")

    if not os.path.exists("logs.txt"):
        await message.answer("Список пользователей пуст.")
        return

    user_ids = set()
    with open("logs.txt", "r", encoding="utf-8") as f:
        for line in f:
            if "ID:" in line:
                try:
                    uid = int(line.split("ID:")[1].split("]")[0].strip())
                    user_ids.add(uid)
                except Exception:
                    pass

    count = 0
    for uid in user_ids:
        try:
            await bot.send_message(uid, f"📢 **Сообщение от администратора:**\n\n{text_to_send}", parse_mode="Markdown")
            count += 1
            await asyncio.sleep(0.05)
        except Exception:
            pass

    await message.answer(f"✅ Успешно отправлено **{count}** пользователям!", parse_mode="Markdown")

# --- 7. РАЗДЕЛ: КНОПКИ МЕНЮ И НОВЫЕ ФИЧИ ---

# 🎱 Шар судьбы
@dp.callback_query(F.data == "btn_magic_8ball")
async def cb_magic_8ball(cb: types.CallbackQuery):
    await cb.answer()
    log_action(cb.from_user, "🎱 Нажал Шар судьбы")
    answers = [
        "Бесспорно! 🎯", "Мне кажется — да. 👍", "Пока не ясно, попробуй снова. 🎲",
        "Даже не думай. ❌", "Мой ответ — НЕТ. 🛑", "Знаки говорят — ДА! ✨",
        "Спроси позже, я сейчас на подзарядке. 🔋"
    ]
    res = random.choice(answers)
    await cb.message.answer(f"🎱 **Шар судьбы говорит:**\n\n_{res}_", parse_mode="Markdown")

# 🗿 Мем дня из TikTok
@dp.callback_query(F.data == "btn_meme_day")
async def cb_meme_day(cb: types.CallbackQuery):
    await cb.answer()
    log_action(cb.from_user, "🗿 Нажал Мем дня")
    memes = [
        "https://i.imgflip.com/1bij.jpg",
        "https://i.imgflip.com/26am.jpg",
        "https://i.imgflip.com/1tlcq4.jpg",
        "https://i.imgflip.com/28j0te.jpg"
    ]
    await cb.message.answer_photo(
        photo=random.choice(memes),
        caption="🗿 **Твой трендовый мем на сегодня!**"
    )

# ☀️ Погода
@dp.callback_query(F.data == "btn_weather_info")
async def cb_weather_info(cb: types.CallbackQuery):
    await cb.answer()
    log_action(cb.from_user, "☀️ Нажал кнопку Погода")
    await cb.message.answer("☀️ Напиши в чат слово `Погода` и название города.\nПример: `Погода Москва` или `Погода Чебоксары`", parse_mode="Markdown")

# 🎧 Плейлист под вайб
@dp.callback_query(F.data == "btn_vibe_playlist")
async def cb_vibe_playlist(cb: types.CallbackQuery):
    await cb.answer()
    log_action(cb.from_user, "🎧 Нажал Плейлист под вайб")
    vibes = {
        "🔥 Дрилл / Фонк": ["DVRST - Close Eyes", "Ghostemane - Fedora", "Shadowraze - Mode Ablaze"],
        "🎧 Чилл / Лоу-фай": ["Lofi Girl - Study Beats", "Kudasaibeats - The Girl I Haven't Met"],
        "💪 Тренировка": ["Mick Gordon - BFG 10000", "Prodigy - Voodoo People"]
    }
    
    msg = "🎧 **Подборка треков по вайбам:**\n\n"
    for vibe, tracks in vibes.items():
        msg += f"**{vibe}:**\n" + "\n".join([f"• {t}" for t in tracks]) + "\n\n"
    
    await cb.message.answer(msg, parse_mode="Markdown")

# 📜 Текст песни
@dp.callback_query(F.data == "btn_lyrics_info")
async def cb_lyrics_info(cb: types.CallbackQuery):
    await cb.answer()
    log_action(cb.from_user, "📜 Нажал Текст песни")
    await cb.message.answer("📜 Напиши в чат слово `Текст` и название песни.\nПример: `Текст Miyagi Патрон`", parse_mode="Markdown")

# ⭐ Избранное
@dp.callback_query(F.data == "btn_favorites")
async def cb_favorites(cb: types.CallbackQuery):
    await cb.answer()
    log_action(cb.from_user, "⭐ Открыл Избранное")
    user_id = cb.from_user.id
    favs = USER_FAVORITES.get(user_id, [])
    if not favs:
        await cb.message.answer("⭐ У тебя пока нет сохранённых треков.")
    else:
        tracks = "\n".join([f"🎵 {t}" for t in favs])
        await cb.message.answer(f"⭐ **Твоё Избранное:**\n\n{tracks}", parse_mode="Markdown")

# 📥 Скачать по ссылке
@dp.callback_query(F.data == "btn_download_link")
async def cb_download_link(cb: types.CallbackQuery):
    await cb.answer()
    log_action(cb.from_user, "📥 Нажал Скачать по ссылке")
    await cb.message.answer("📥 **Отправь ссылку на трек или видео с YouTube / VK прямо в чат!**", parse_mode="Markdown")

@dp.callback_query(F.data == "btn_top_chart")
async def cb_top_chart(cb: types.CallbackQuery):
    await cb.answer()
    log_action(cb.from_user, "🔘 Нажал кнопку: Топ треков недели")
    
    top_tracks = ["Miyagi & Эндшпиль", "MACAN", "Xcho", "Гио Пика"]
    buttons = [[InlineKeyboardButton(text=f"🔥 Популярное: {artist}", callback_data=f"search_{artist}")] for artist in top_tracks]
    buttons.append([InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="btn_back_to_menu")])
    
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await cb.message.edit_caption(caption="🔥 **Чарт популярных исполнителей этой недели:**\nНажми на любого, чтобы найти его треки:", reply_markup=kb, parse_mode="Markdown")

@dp.callback_query(F.data == "btn_random_track")
async def cb_random_track(cb: types.CallbackQuery):
    await cb.answer()
    log_action(cb.from_user, "🎲 Нажал кнопку: Случайный трек")
    
    random_artists = ["Miyagi", "KIZARU", "Skryptonite", "MACAN", "Pharaoh", "Rauf & Faik", "Markul"]
    chosen = random.choice(random_artists)
    
    log_action(cb.from_user, f"🎲 Случайный выбор выпал на: {chosen}")
    status_msg = await cb.message.answer(f"🎲 Выбран случайный исполнитель: **{chosen}**! Ищу треки...", parse_mode="Markdown")
    
    loop = asyncio.get_event_loop()
    results = await loop.run_in_executor(None, search_youtube_tracks, chosen)

    if results:
        buttons = []
        for t in results:
            buttons.append([
                InlineKeyboardButton(text=f"🎵 {t['title']}", callback_data=f"dl_{t['id']}"),
                InlineKeyboardButton(text="⭐", callback_data=f"fav_{t['id']}")
            ])
        buttons.append([InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="btn_back_to_menu")])
        await status_msg.edit_text(f"🎲 **Случайная подборка ({chosen}):**", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="Markdown")
    else:
        await status_msg.edit_text("❌ Ничего не найдено.")

@dp.callback_query(F.data.startswith("search_"))
async def cb_search_from_chart(cb: types.CallbackQuery):
    await cb.answer()
    query = cb.data.replace("search_", "")
    log_action(cb.from_user, f"🔥 Выбрал из чарта исполнителя: {query}")
    
    status_msg = await cb.message.answer(f"⚡️ Ищу лучшие треки **{query}**...", parse_mode="Markdown")
    loop = asyncio.get_event_loop()
    results = await loop.run_in_executor(None, search_youtube_tracks, query)

    if results:
        buttons = []
        for t in results:
            buttons.append([
                InlineKeyboardButton(text=f"🎵 {t['title']}", callback_data=f"dl_{t['id']}"),
                InlineKeyboardButton(text="⭐", callback_data=f"fav_{t['id']}")
            ])
        buttons.append([InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="btn_back_to_menu")])
        await status_msg.edit_text(f"🎯 **Результаты по запросу {query}:**", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="Markdown")
    else:
        await status_msg.edit_text("❌ Ничего не найдено.")

@dp.callback_query(F.data == "btn_back_to_menu")
async def cb_back_to_menu(cb: types.CallbackQuery):
    await cb.answer()
    log_action(cb.from_user, "↩️ Нажал кнопку: Назад в меню")
    welcome_text = (
        f"🎧 **Welcome to Music Space, {cb.from_user.first_name}!** 🎧\n"
        "⚡️ ═════════════════════ ⚡️\n\n"
        "👇 **Выбери действие ниже или просто напиши название песни в чат:**"
    )
    await cb.message.edit_caption(caption=welcome_text, reply_markup=get_main_keyboard(), parse_mode="Markdown")

@dp.callback_query(F.data == "btn_search_music")
async def cb_search_music(cb: types.CallbackQuery):
    await cb.answer()
    log_action(cb.from_user, "🔘 Нажал кнопку: Поиск песни по названию")
    await cb.message.answer("🔎 **Просто напиши название песни в чат!**\nПример: `Miyagi Патрон`", parse_mode="Markdown")

@dp.callback_query(F.data == "btn_screenshot_info")
async def cb_screenshot_info(cb: types.CallbackQuery):
    await cb.answer()
    log_action(cb.from_user, "📸 Нажал кнопку: Поиск по скриншоту")
    await cb.message.answer("📸 **Отправь скриншот плеера, TikTok или обложки песни!**\nИИ распознает трек и найдёт его для скачивания.", parse_mode="Markdown")

@dp.callback_query(F.data == "btn_shazam_info")
async def cb_shazam_info(cb: types.CallbackQuery):
    await cb.answer()
    log_action(cb.from_user, "🎙️ Нажал кнопку: Shazam (инструкция)")
    await cb.message.answer("🎙️ **Распознавание:** Скинь в чат голосовое сообщение, кружок или видео!", parse_mode="Markdown")

# Добавление в Избранное по кнопке
@dp.callback_query(F.data.startswith("fav_"))
async def cb_add_favorite(cb: types.CallbackQuery):
    track_id = cb.data.replace("fav_", "")
    user_id = cb.from_user.id
    if user_id not in USER_FAVORITES:
        USER_FAVORITES[user_id] = []
    
    track_title = f"Трек ID: {track_id}"
    if track_title not in USER_FAVORITES[user_id]:
        USER_FAVORITES[user_id].append(track_title)
        await cb.answer("⭐ Добавлено в избранное!", show_alert=True)
    else:
        await cb.answer("Уже есть в избранном!", show_alert=True)

# --- 8. ПОИСК, ПОГОДА, ТЕКСТЫ И СКАЧИВАНИЕ ПО ТЕКСТУ ---
@dp.message(F.text & ~F.text.startswith("/"))
@dp.message(Command("music"))
async def process_text_input(message: types.Message):
    query = message.text.replace("/music", "").strip() if message.text.startswith("/music") else message.text.strip()
    
    if not query:
        await message.answer("⚠️ Напиши название песни!")
        return

    # Обработка команды Погода
    if query.lower().startswith("погода"):
        city = query[6:].strip()
        if not city:
            await message.answer("☀️ Укажи город. Пример: `Погода Москва`", parse_mode="Markdown")
            return
        try:
            res = requests.get(f"https://wttr.in/{city}?format=%C+%t+%w").text
            await message.answer(f"☀️ **Погода в {city}:**\n{res}")
        except Exception:
            await message.answer("❌ Не удалось получить данные о погоде.")
        return

    # Обработка команды Текст песни
    if query.lower().startswith("текст"):
        song = query[5:].strip()
        if not song:
            await message.answer("📜 Напиши название песни после слова Текст.", parse_mode="Markdown")
            return
        
        status_msg = await message.answer(f"🔍 Ищу текст песни **{song}**...", parse_mode="Markdown")
        try:
            prompt = f"Напиши полный текст песни {song}. Если текст слишком длинный, напиши основные куплеты и припев."
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, lambda: gemini_model.generate_content(prompt))
            await status_msg.edit_text(f"📜 **Текст песни {song}:**\n\n{response.text[:3800]}")
        except Exception as e:
            await status_msg.edit_text("❌ Ошибка при поиске текста песни.")
        return

    # Обработка ссылок (YouTube / VK)
    if query.startswith("http://") or query.startswith("https://"):
        log_action(message.from_user, f"📥 Отправил ссылку на скачивание: {query}")
        status_msg = await message.answer("🚀 Загружаю аудио по вашей ссылке...")
        try:
            loop = asyncio.get_event_loop()
            file_path, title = await loop.run_in_executor(None, download_audio_by_id, query)
            
            audio_file = types.FSInputFile(file_path)
            await message.answer_audio(audio=audio_file, caption=f"🎶 **{title}**", parse_mode="Markdown")
            await status_msg.delete()
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            await status_msg.edit_text("❌ Ошибка при скачивании по ссылке.")
        return

    # Обычный поиск песни
    log_action(message.from_user, f"🔎 Ищет песню: '{query}'")

    status_msg = await message.answer(f"⚡️ Мгновенный поиск: **{query}**...", parse_mode="Markdown")

    loop = asyncio.get_event_loop()
    results = await loop.run_in_executor(None, search_youtube_tracks, query)

    if not results:
        log_action(message.from_user, f"❌ По запросу '{query}' ничего не найдено")
        await status_msg.edit_text("❌ Ничего не найдено. Попробуй уточнить запрос.")
        return

    buttons = []
    for track in results:
        buttons.append([
            InlineKeyboardButton(text=f"🎵 {track['title']}", callback_data=f"dl_{track['id']}"),
            InlineKeyboardButton(text="⭐", callback_data=f"fav_{track['id']}")
        ])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await status_msg.edit_text("🎯 **Найдено несколько вариантов! Выбери нужный:**", reply_markup=kb, parse_mode="Markdown")

@dp.callback_query(F.data.startswith("dl_"))
async def cb_download_selected(cb: types.CallbackQuery):
    await cb.answer()
    video_id = cb.data.replace("dl_", "")
    log_action(cb.from_user, f"📥 Нажал скачать трек с ID: {video_id}")
    
    status_msg = await cb.message.answer("🚀 Загружаю выбранный трек в чат...")
    
    try:
        loop = asyncio.get_event_loop()
        file_path, title = await loop.run_in_executor(None, download_audio_by_id, video_id)
        
        log_action(cb.from_user, f"✅ Успешно скачан и отправляется: {title}")
        audio_file = types.FSInputFile(file_path)
        await cb.message.answer_audio(audio=audio_file, caption=f"🎶 **{title}**", parse_mode="Markdown")
        
        await status_msg.delete()
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        log_action(cb.from_user, f"💥 Ошибка скачивания трека {video_id}: {e}")
        await status_msg.edit_text("❌ Ошибка при скачивании трека.")

# --- 9. ОБРАБОТКА СКРИНШОТОВ (Gemini AI) ---
@dp.message(F.photo)
async def handle_photo_search(message: types.Message):
    log_action(message.from_user, "📸 Отправил фото/скриншот для поиска трека")

    status_msg = await message.answer("👁️ Анализирую скриншот...")
    temp_img_path = f"temp_{message.photo[-1].file_id}.jpg"

    try:
        file = await bot.get_file(message.photo[-1].file_id)
        await bot.download_file(file.file_path, temp_img_path)

        image = Image.open(temp_img_path)
        prompt = (
            "Определи песню или исполнителя по этому скриншоту/обложке. "
            "Ответь ТОЛЬКО в формате: Исполнитель - Название песни. "
            "Если на скриншоте нет информации о музыке, напиши 'NOT_FOUND'."
        )

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None, lambda: gemini_model.generate_content([prompt, image])
        )
        extracted_text = response.text.strip()

        if os.path.exists(temp_img_path):
            os.remove(temp_img_path)

        if "NOT_FOUND" in extracted_text or not extracted_text:
            await status_msg.edit_text("❌ Не удалось найти информацию о треке на этой картинке.")
            return

        log_action(message.from_user, f"✨ Gemini нашел на скриншоте: {extracted_text}")
        await status_msg.edit_text(
            f"🎯 **Нашел на картинке:** `{extracted_text}`\nИщу аудиозаписи...",
            parse_mode="Markdown"
        )

        results = await loop.run_in_executor(None, search_youtube_tracks, extracted_text)

        if results:
            buttons = []
            for t in results:
                buttons.append([
                    InlineKeyboardButton(text=f"🎵 {t['title']}", callback_data=f"dl_{t['id']}"),
                    InlineKeyboardButton(text="⭐", callback_data=f"fav_{t['id']}")
                ])
            buttons.append([InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="btn_back_to_menu")])
            await status_msg.edit_text(
                f"🎶 **Результаты по скриншоту ({extracted_text}):**",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
                parse_mode="Markdown"
            )
        else:
            await status_msg.edit_text(f"❌ Название `{extracted_text}` распознано, но трек не найден.", parse_mode="Markdown")

    except Exception as e:
        log_action(message.from_user, f"💥 Ошибка анализа скриншота: {e}")
        await status_msg.edit_text(f"❌ Ошибка при распознавании картинки: {str(e)}")
        if os.path.exists(temp_img_path):
            os.remove(temp_img_path)

# --- 10. ГОЛОСОВЫЕ, ВИДЕО И SHAZAM ---
@dp.message(F.voice | F.video_note | F.audio | F.video)
async def handle_media(message: types.Message):
    media_type = "Голосовое" if message.voice else "Кружок" if message.video_note else "Аудио" if message.audio else "Видео"
    log_action(message.from_user, f"🎙️ Отправил {media_type} для распознавания")

    if message.voice: file_id = message.voice.file_id
    elif message.video_note: file_id = message.video_note.file_id
    elif message.audio: file_id = message.audio.file_id
    elif message.video: file_id = message.video.file_id
    else: return

    status_msg = await message.answer("🎧 **Слушаю обрывок...**", parse_mode="Markdown")
    temp_file = "sample.ogg"

    try:
        file = await bot.get_file(file_id)
        await bot.download_file(file.file_path, temp_file)

        loop = asyncio.get_event_loop()
        track_name = await loop.run_in_executor(None, recognize_audio_file, temp_file)

        if os.path.exists(temp_file):
            os.remove(temp_file)

        if not track_name:
            log_action(message.from_user, "❌ Shazam не смог распознать звук")
            await status_msg.edit_text("❌ Не удалось распознать обрывок. Попробуй скинуть более четкий фрагмент.")
            return

        log_action(message.from_user, f"✨ Shazam успешно распознал: {track_name}")
        await status_msg.edit_text(f"🔍 **Распознано:** {track_name}\nИщу варианты... 🚀", parse_mode="Markdown")
        
        results = await loop.run_in_executor(None, search_youtube_tracks, track_name)
        if results:
            buttons = []
            for t in results:
                buttons.append([
                    InlineKeyboardButton(text=f"🎵 {t['title']}", callback_data=f"dl_{t['id']}"),
                    InlineKeyboardButton(text="⭐", callback_data=f"fav_{t['id']}")
                ])
            await status_msg.edit_text(f"🎶 **Распознано:** {track_name}\nВыбери вариант для скачивания:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="Markdown")
        else:
            await status_msg.edit_text("❌ Трек распознан, но не найден для скачивания.")

    except Exception as e:
        log_action(message.from_user, f"💥 Ошибка распознавания: {e}")
        await status_msg.edit_text("❌ Ошибка при обработке.")
        if os.path.exists(temp_file):
            os.remove(temp_file)

# --- 11. ЗАПУСК ---
async def main():
    print("🚀 Бот успешно запущен! Ожидание действий пользователей...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
