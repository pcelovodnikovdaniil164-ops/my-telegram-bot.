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

IMAGE_URL = "AgACAgIAAxkBAAEtcrjQexLwhpT41qs4qe1hf1gXHI53aWACqh1rG-T02Utgkjd3RSHWOdAEaAwIaA3gAAz0E"

# --- НАСТРОЙКА GEMINI API ---
GEMINI_KEY = "AQ.Ab8RN6Lq9dKAY279ar8rVhuQCThmVZGp2L61XRDFUxzyOZqGlQ"
genai.configure(api_key=GEMINI_KEY)
gemini_model = genai.GenerativeModel("gemini-1.5-flash")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Хелпер для удобного лога в консоль и файл
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

# --- 2. СКАЧИВАНИЕ ТРЕКА ПО ID ---
def download_audio_by_id(video_id):
    url = f"https://www.youtube.com/watch?v={video_id}"
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': f'song_{video_id}.%(ext)s',
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
        [InlineKeyboardButton(text="🔎 Искать песню по названию", callback_data="btn_search_music")],
        [InlineKeyboardButton(text="📸 Поиск трека по скриншоту", callback_data="btn_screenshot_info")],
        [InlineKeyboardButton(text="🔥 Топ треков недели", callback_data="btn_top_chart")],
        [InlineKeyboardButton(text="🎲 Случайный трек", callback_data="btn_random_track")],
        [InlineKeyboardButton(text="🎙️ Распознать обрывок (Shazam)", callback_data="btn_shazam_info")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# --- 5. СТАРТ И МЕНЮ ---
@dp.message(CommandStart())
@dp.message(Command("menu"))
async def send_menu(message: types.Message):
    log_action(message.from_user, "🟢 Запустил бота / вызвал /menu")

    welcome_text = (
        f"✨ **Привет, {message.from_user.first_name}!** ✨\n"
        "━━━━━ • 🤖 • ━━━━━\n"
        "Я твой личный музыкальный помощник!\n\n"
        "🎵 **Что я умею:**\n"
        "├ 🔎 Мгновенный поиск песен по названию\n"
        "├ 📸 Поиск трека по скриншоту/фото (ИИ Gemini)\n"
        "├ 🎧 Распознавание голосовых и видео (Shazam)\n"
        "├ 🔥 Актуальные треки недели\n"
        "└ 🎲 Случайная музыка под настроение\n\n"
        "👇 **Выбери действие ниже или просто напиши название песни / скинь скриншот:**"
    )

    try:
        await message.answer_photo(
            photo=IMAGE_URL,
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

# --- 7. РАЗДЕЛ: КНОПКИ МЕНЮ И ЧАРТЫ ---

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
        buttons = [[InlineKeyboardButton(text=f"🎵 {t['title']}", callback_data=f"dl_{t['id']}")] for t in results]
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
        buttons = [[InlineKeyboardButton(text=f"🎵 {t['title']}", callback_data=f"dl_{t['id']}")] for t in results]
        buttons.append([InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="btn_back_to_menu")])
        await status_msg.edit_text(f"🎯 **Результаты по запросу {query}:**", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="Markdown")
    else:
        await status_msg.edit_text("❌ Ничего не найдено.")

@dp.callback_query(F.data == "btn_back_to_menu")
async def cb_back_to_menu(cb: types.CallbackQuery):
    await cb.answer()
    log_action(cb.from_user, "↩️ Нажал кнопку: Назад в меню")
    welcome_text = (
        f"✨ **Привет, {cb.from_user.first_name}!** ✨\n"
        "━━━━━ • 🤖 • ━━━━━\n"
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

# --- 8. ПОИСК И СКАЧИВАНИЕ ПО ТЕКСТУ ---
@dp.message(F.text & ~F.text.startswith("/"))
@dp.message(Command("music"))
async def process_search(message: types.Message):
    query = message.text.replace("/music", "").strip() if message.text.startswith("/music") else message.text.strip()
    
    if not query:
        await message.answer("⚠️ Напиши название песни!")
        return

    log_action(message.from_user, f"🔎 Ищет песню: '{query}'")

    status_msg = await message.answer(f"⚡️ Мгновенный поиск: **{query}**...", parse_mode="Markdown")

    loop = asyncio.get_event_loop()
    results = await loop.run_in_executor(None, search_youtube_tracks, query)

    if not results:
        log_action(message.from_user, f"❌ По запросу '{query}' ничего не найдено")
        await status_msg.edit_text("❌ Ничего не найдено. Попробуй уточнить запрос.")
        return

    buttons = [[InlineKeyboardButton(text=f"🎵 {track['title']}", callback_data=f"dl_{track['id']}")] for track in results]
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
            buttons = [[InlineKeyboardButton(text=f"🎵 {t['title']}", callback_data=f"dl_{t['id']}")] for t in results]
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
            buttons = [[InlineKeyboardButton(text=f"🎵 {t['title']}", callback_data=f"dl_{t['id']}")] for t in results]
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
