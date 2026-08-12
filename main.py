import asyncio
import os
import random
import requests
import qrcode
from datetime import datetime
from gtts import gTTS
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command, CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, FSInputFile, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import yt_dlp

TOKEN = "8171123432:AAE3oBJMtRBiryyJPrODcvZLqSo3qOLY1Cs"
ADMIN_ID = 6557367300
IMAGE_URL = "https://i.postimg.cc/mD8N1J44/music-bot-banner.jpg"

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# --- ФУНКЦИЯ ЛОГИРОВАНИЯ ---
def log_user_action(user: types.User, action_type: str, details: str = ""):
    time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    username = f"@{user.username}" if user.username else "Нет юзернейма"
    first_name = user.first_name or "Без имени"
    user_id = user.id
    
    log_line = f"[{time_str}] ID: {user_id} | User: {username} ({first_name}) | Действие: {action_type} | Детали: {details}\n"
    
    # Вывод в консоль Pydroid
    print(log_line.strip())
    
    # Сохранение в файл логов
    with open("user_logs.txt", "a", encoding="utf-8") as f:
        f.write(log_line)

# --- СОСТОЯНИЯ (FSM) ---
class UserStates(StatesGroup):
    waiting_support = State()
    waiting_reply = State()
    waiting_lyrics = State()
    waiting_review = State()
    waiting_qr = State()
    waiting_tts = State()
    waiting_calc = State()
    waiting_weather = State()
    waiting_ball = State()

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---
def save_review(name, text):
    with open("reviews.txt", "a", encoding="utf-8") as f:
        f.write(f"⭐ {name}: {text}\n")

def get_reviews():
    if not os.path.exists("reviews.txt"):
        return "Пока нет ни одного отзыва."
    with open("reviews.txt", "r", encoding="utf-8") as f:
        lines = f.readlines()
        return "".join(lines[-15:]) if lines else "Пока нет ни одного отзыва."

def search_music(query, max_res=4):
    ydl_opts = {'quiet': True, 'extract_flat': True, 'skip_download': True}
    res = []
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch{max_res}:{query}", download=False)
            if info and 'entries' in info:
                for e in info['entries']:
                    if e.get('id'):
                        res.append({'id': e.get('id'), 'title': e.get('title', 'Трек')[:35]})
    except Exception:
        pass
    return res

def download_music(v_id):
    url = f"https://www.youtube.com/watch?v={v_id}"
    ydl_opts = {'format': 'bestaudio/best', 'outtmpl': f'song_{v_id}.%(ext)s', 'quiet': True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return ydl.prepare_filename(info), info.get('title', 'Музыка')

def get_lyrics(query):
    try:
        res = requests.get(f"https://api.lyrics.ovh/v1/{query}").json()
        return res.get("lyrics")[:3500] if "lyrics" in res else None
    except Exception:
        return None

# --- КЛАВИАТУРЫ ---
def get_main_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎵 Поиск музыки", callback_data="btn_search")],
        [InlineKeyboardButton(text="📜 Текст песни", callback_data="btn_lyrics"), InlineKeyboardButton(text="🎙️ Озвучить текст", callback_data="btn_tts")],
        [InlineKeyboardButton(text="📱 QR-код", callback_data="btn_qr"), InlineKeyboardButton(text="🔢 Калькулятор", callback_data="btn_calc")],
        [InlineKeyboardButton(text="☁️ Погода", callback_data="btn_weather"), InlineKeyboardButton(text="🤡 Мем дня", callback_data="btn_meme")],
        [InlineKeyboardButton(text="🎲 Бросить кость", callback_data="btn_dice"), InlineKeyboardButton(text="🎱 Шар судьбы", callback_data="btn_ball")],
        [InlineKeyboardButton(text="⭐ Оставить отзыв", callback_data="btn_add_review"), InlineKeyboardButton(text="📖 Все отзывы", callback_data="btn_get_reviews")],
        [InlineKeyboardButton(text="👨‍💻 Написать админу", callback_data="btn_admin")]
    ])

# --- СТАРТ И МЕНЮ ---
@dp.message(CommandStart())
@dp.message(Command("menu"))
async def start_cmd(msg: types.Message, state: FSMContext):
    await state.clear()
    log_user_action(msg.from_user, "Команда /start или /menu")
    
    welcome = (
        f"⚡ **Привет, {msg.from_user.first_name}!** ⚡\n"
        "━━━━━━━ • 🎧 • ━━━━━━━\n"
        "Я твой личный комбайн-помощник!\n\n"
        "🎶 **Музыка:** Поиск, тексты, озвучка\n"
        "🛠️ **Утилиты:** QR-коды, погода, калькулятор\n"
        "🎲 **Развлечения:** Кости, мемы, шар предсказаний\n\n"
        "👇 **Выбери нужный раздел:**"
    )
    try:
        await msg.answer_photo(photo=IMAGE_URL, caption=welcome, reply_markup=get_main_keyboard(), parse_mode="Markdown")
    except Exception:
        await msg.answer(welcome, reply_markup=get_main_keyboard(), parse_mode="Markdown")

# --- ЛОГИРОВАНИЕ ВИДЕО И КОНТАКТОВ ---

# Логирование отправленных видео/кружочков
@dp.message(F.video | F.video_note)
async def log_video_handler(msg: types.Message):
    v_type = "Видео-сообщение (кружок)" if msg.video_note else "Обычное видео"
    log_user_action(msg.from_user, f"Прислал {v_type}", f"File ID: {msg.video.file_id if msg.video else msg.video_note.file_id}")
    
    # Уведомление админу о видео
    await bot.send_message(
        ADMIN_ID, 
        f"📹 **Пользователь прислал {v_type}!**\nИмя: {msg.from_user.first_name}\nID: `{msg.from_user.id}`\nUsername: @{msg.from_user.username}",
        parse_mode="Markdown"
    )
    # Пересылка самого видео админу
    await msg.forward(ADMIN_ID)
    await msg.answer("✅ Видео получено!")

# Логирование отправки номера телефона (если пользователь поделился контактом)
@dp.message(F.contact)
async def log_contact_handler(msg: types.Message):
    phone = msg.contact.phone_number
    log_user_action(msg.from_user, "Поделился номером телефона", f"Номер: {phone}")
    await bot.send_message(ADMIN_ID, f"📱 **Новый номер телефона!**\nUser: {msg.from_user.first_name} (`{msg.from_user.id}`)\nТелефон: `{phone}`", parse_mode="Markdown")

# --- СТАТИСТИКА И ЛОГИ (ДЛЯ АДМИНА) ---
@dp.message(Command("stats"))
async def stats_cmd(msg: types.Message):
    if msg.from_user.id != ADMIN_ID: return
    rev_count = len(get_reviews().split("\n")) if os.path.exists("reviews.txt") else 0
    await msg.answer(f"📊 **Статистика бота:**\n\n- Сохраненных отзывов: {rev_count}\n- Статус: Активен ✅", parse_mode="Markdown")

@dp.message(Command("logs"))
async def get_logs_cmd(msg: types.Message):
    if msg.from_user.id != ADMIN_ID: return
    if os.path.exists("user_logs.txt"):
        await msg.answer_document(FSInputFile("user_logs.txt"), caption="📜 Файл полных логов активности пользователей.")
    else:
        await msg.answer("❌ Логов пока нет.")

# --- ОБРАБОТЧИКИ КНОПОК И ФУНКЦИЙ ---

@dp.callback_query(F.data == "btn_weather")
async def cb_weather(cb: types.CallbackQuery, state: FSMContext):
    log_user_action(cb.from_user, "Нажал 'Погода'")
    await cb.answer()
    await state.set_state(UserStates.waiting_weather)
    await cb.message.answer("☁️ **Напиши название города:**", parse_mode="Markdown")

@dp.message(UserStates.waiting_weather)
async def proc_weather(msg: types.Message, state: FSMContext):
    log_user_action(msg.from_user, "Запрос погоды", msg.text)
    await state.clear()
    try:
        res = requests.get(f"https://wttr.in/{msg.text.strip()}?format=3").text
        await msg.answer(f"🌡️ **Погода:** {res}")
    except Exception:
        await msg.answer("❌ Не удалось найти город.")

@dp.callback_query(F.data == "btn_meme")
async def cb_meme(cb: types.CallbackQuery):
    log_user_action(cb.from_user, "Запросил мем")
    await cb.answer("Ищу мем...")
    try:
        url = requests.get("https://meme-api.com/gimme").json().get('url')
        await cb.message.answer_photo(photo=url, caption="😂 Держи свежий мем!")
    except Exception:
        await cb.message.answer("❌ Не удалось загрузить мем.")

@dp.callback_query(F.data == "btn_dice")
async def cb_dice(cb: types.CallbackQuery):
    log_user_action(cb.from_user, "Бросил кости")
    await cb.answer()
    await cb.message.answer_dice(emoji="🎲")

@dp.callback_query(F.data == "btn_ball")
async def cb_ball(cb: types.CallbackQuery, state: FSMContext):
    log_user_action(cb.from_user, "Открыл Шар судьбы")
    await cb.answer()
    await state.set_state(UserStates.waiting_ball)
    await cb.message.answer("🎱 **Задай мне любой вопрос, на который можно ответить 'Да' или 'Нет':**", parse_mode="Markdown")

@dp.message(UserStates.waiting_ball)
async def proc_ball(msg: types.Message, state: FSMContext):
    log_user_action(msg.from_user, "Вопрос к Шару судьбы", msg.text)
    await state.clear()
    ans = ["Бесспорно!", "Мне кажется — да.", "Знаки говорят — нет.", "Даже не думай.", "Спроси позже.", "100% да!"]
    await msg.answer(f"🎱 **Шарик отвечает:** {random.choice(ans)}")

@dp.callback_query(F.data == "btn_calc")
async def cb_calc(cb: types.CallbackQuery, state: FSMContext):
    log_user_action(cb.from_user, "Открыл калькулятор")
    await cb.answer()
    await state.set_state(UserStates.waiting_calc)
    await cb.message.answer("🔢 **Введи математическое выражение** (например: `25 * 4 + 10`):", parse_mode="Markdown")

@dp.message(UserStates.waiting_calc)
async def proc_calc(msg: types.Message, state: FSMContext):
    log_user_action(msg.from_user, "Считает пример", msg.text)
    await state.clear()
    allowed = "0123456789+-*/(). "
    if all(c in allowed for c in msg.text):
        try:
            await msg.answer(f"💡 **Результат:** `{eval(msg.text)}`", parse_mode="Markdown")
        except Exception:
            await msg.answer("❌ Ошибка в расчетах.")
    else:
        await msg.answer("❌ Можно использовать только цифры и знаки + - * / ( )")

@dp.callback_query(F.data == "btn_qr")
async def cb_qr(cb: types.CallbackQuery, state: FSMContext):
    log_user_action(cb.from_user, "Запросил генерацию QR")
    await cb.answer()
    await state.set_state(UserStates.waiting_qr)
    await cb.message.answer("📱 **Напиши текст или ссылку для QR-кода:**", parse_mode="Markdown")

@dp.message(UserStates.waiting_qr)
async def proc_qr(msg: types.Message, state: FSMContext):
    log_user_action(msg.from_user, "Создал QR-код", msg.text)
    await state.clear()
    img = qrcode.make(msg.text)
    img.save("qr.png")
    await msg.answer_photo(photo=FSInputFile("qr.png"), caption="✅ Ваш QR-код готов!")
    if os.path.exists("qr.png"): os.remove("qr.png")

@dp.callback_query(F.data == "btn_tts")
async def cb_tts(cb: types.CallbackQuery, state: FSMContext):
    log_user_action(cb.from_user, "Запросил озвучку TTS")
    await cb.answer()
    await state.set_state(UserStates.waiting_tts)
    await cb.message.answer("🎙️ **Напиши текст, который нужно озвучить:**", parse_mode="Markdown")

@dp.message(UserStates.waiting_tts)
async def proc_tts(msg: types.Message, state: FSMContext):
    log_user_action(msg.from_user, "Озвучил текст", msg.text)
    await state.clear()
    tts = gTTS(msg.text, lang='ru')
    tts.save("voice.mp3")
    await msg.answer_voice(voice=FSInputFile("voice.mp3"))
    if os.path.exists("voice.mp3"): os.remove("voice.mp3")

@dp.callback_query(F.data == "btn_add_review")
async def cb_add_rev(cb: types.CallbackQuery, state: FSMContext):
    log_user_action(cb.from_user, "Нажал 'Оставить отзыв'")
    await cb.answer()
    await state.set_state(UserStates.waiting_review)
    await cb.message.answer("✍️ **Напиши отзыв о боте:**", parse_mode="Markdown")

@dp.message(UserStates.waiting_review)
async def proc_rev(msg: types.Message, state: FSMContext):
    log_user_action(msg.from_user, "Оставил отзыв", msg.text)
    await state.clear()
    save_review(msg.from_user.first_name, msg.text)
    await msg.answer("✅ Спасибо! Отзыв опубликован.")

@dp.callback_query(F.data == "btn_get_reviews")
async def cb_get_rev(cb: types.CallbackQuery):
    log_user_action(cb.from_user, "Просмотрел отзывы")
    await cb.answer()
    await cb.message.answer(f"📖 **Отзывы пользователей:**\n\n{get_reviews()}", parse_mode="Markdown")

@dp.callback_query(F.data == "btn_admin")
async def cb_admin(cb: types.CallbackQuery, state: FSMContext):
    log_user_action(cb.from_user, "Нажал 'Написать админу'")
    await cb.answer()
    await state.set_state(UserStates.waiting_support)
    await cb.message.answer("📝 **Напишите ваше сообщение админу:**", parse_mode="Markdown")

@dp.message(UserStates.waiting_support)
async def proc_support(msg: types.Message, state: FSMContext):
    log_user_action(msg.from_user, "Написал админу", msg.text)
    await state.clear()
    btn = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="💬 Ответить", callback_data=f"reply_{msg.from_user.id}")]])
    await bot.send_message(ADMIN_ID, f"📩 **Сообщение от:** {msg.from_user.first_name} (`{msg.from_user.id}`)\nUsername: @{msg.from_user.username}\n\n{msg.text}", reply_markup=btn, parse_mode="Markdown")
    await msg.answer("✅ Отправлено админу!")

@dp.callback_query(F.data.startswith("reply_"))
async def cb_reply_start(cb: types.CallbackQuery, state: FSMContext):
    if cb.from_user.id != ADMIN_ID: return
    await cb.answer()
    uid = cb.data.replace("reply_", "")
    await state.update_data(target_id=uid)
    await state.set_state(UserStates.waiting_reply)
    await cb.message.answer(f"✍️ Напиши ответ пользователю `{uid}`:", parse_mode="Markdown")

@dp.message(UserStates.waiting_reply)
async def proc_reply(msg: types.Message, state: FSMContext):
    if msg.from_user.id != ADMIN_ID: return
    data = await state.get_data()
    await state.clear()
    try:
        await bot.send_message(data.get("target_id"), f"🔔 **Ответ от админа:**\n\n{msg.text}", parse_mode="Markdown")
        await msg.answer("✅ Ответ доставлен!")
    except Exception as e:
        await msg.answer(f"❌ Не удалось доставить: {e}")

@dp.callback_query(F.data == "btn_search")
async def cb_search_info(cb: types.CallbackQuery):
    log_user_action(cb.from_user, "Нажал 'Поиск музыки'")
    await cb.answer()
    await cb.message.answer("🔎 **Просто отправь название песни текстом в чат!**", parse_mode="Markdown")

@dp.message(F.text & ~F.text.startswith("/"))
async def search_handler(msg: types.Message):
    log_user_action(msg.from_user, "Поиск трека", msg.text)
    status = await msg.answer("⚡ Ищу треки...")
    res = await asyncio.to_thread(search_music, msg.text)
    if not res:
        return await status.edit_text("❌ Ничего не найдено.")
    btns = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f"🎵 {t['title']}", callback_data=f"dl_{t['id']}")] for t in res])
    await status.edit_text("🎯 **Найденные результаты:**", reply_markup=btns, parse_mode="Markdown")

@dp.callback_query(F.data.startswith("dl_"))
async def download_handler(cb: types.CallbackQuery):
    v_id = cb.data.replace("dl_", "")
    log_user_action(cb.from_user, "Скачивает трек", f"Video ID: {v_id}")
    await cb.answer("Скачиваю...")
    file_path, title = await asyncio.to_thread(download_music, v_id)
    await cb.message.answer_audio(audio=FSInputFile(file_path), caption=f"🎶 **{title}**", parse_mode="Markdown")
    if os.path.exists(file_path): os.remove(file_path)

# --- ЗАПУСК ---
async def main():
    print("🚀 Бот запущен! Все действия пользователей логируются.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
