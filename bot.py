import asyncio
import os
from groq import Groq
from supabase import create_client
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()
groq_client = Groq(api_key=GROQ_API_KEY)
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ==== ТЕКСТЫ НА ДВУХ ЯЗЫКАХ ====
TEXTS = {
    "ru": {
        "btn_balance": "💰 Мой баланс",
        "btn_repair": "🔧 Заявка на ремонт",
        "btn_requests": "📋 Мои заявки",
        "btn_operator": "📞 Связаться с оператором",
        "btn_info": "ℹ️ Информация о ЖК",
        "btn_lang": "🌐 Til / Язык",
        "welcome": "👋 Добро пожаловать в Family Park!\n\nЗдравствуйте, {name}!\nЯ ваш персональный ИИ-помощник. Задайте любой вопрос или выберите пункт меню.",
        "balance": "💰 Ваш текущий баланс: {balance:,} сум\n📅 Следующий платёж: 1 июля 2026",
        "repair": "🔧 Опишите вашу проблему подробно, и я передам заявку в service-отдел.",
        "no_requests": "📋 У вас пока нет заявок.",
        "requests_title": "📋 Ваши заявки:\n\n",
        "operator": "📞 Соединяю вас с оператором...\nВремя ожидания: ~5 минут\n\nИли позвоните: +998 71 000-00-00",
        "info": "🏘️ Family Park\n\n📍 Адрес: г. Самарканд\n🕐 Режим работы: 9:00 - 18:00\n📞 Телефон: +998 71 000-00-00",
        "thinking": "⏳ Думаю...",
        "choose_lang": "Выберите язык / Tilni tanlang:",
        "lang_set": "✅ Язык изменён на русский.",
        "voice_heard": "🎤 Вы сказали: {text}",
    },
    "uz": {
        "btn_balance": "💰 Mening balansim",
        "btn_repair": "🔧 Ta'mirlash arizasi",
        "btn_requests": "📋 Mening arizalarim",
        "btn_operator": "📞 Operator bilan bog'lanish",
        "btn_info": "ℹ️ TJM haqida ma'lumot",
        "btn_lang": "🌐 Til / Язык",
        "welcome": "👋 Family Park'ga xush kelibsiz!\n\nSalom, {name}!\nMen sizning shaxsiy AI-yordamchingizman. Istalgan savol bering yoki menyudan tanlang.",
        "balance": "💰 Sizning joriy balansingiz: {balance:,} so'm\n📅 Keyingi to'lov: 2026-yil 1-iyul",
        "repair": "🔧 Muammoyingizni batafsil yozing, men arizani service-bo'limga yuboraman.",
        "no_requests": "📋 Sizda hozircha arizalar yo'q.",
        "requests_title": "📋 Sizning arizalaringiz:\n\n",
        "operator": "📞 Sizni operator bilan bog'layapman...\nKutish vaqti: ~5 daqiqa\n\nYoki qo'ng'iroq qiling: +998 71 000-00-00",
        "info": "🏘️ Family Park\n\n📍 Manzil: Samarqand sh.\n🕐 Ish vaqti: 9:00 - 18:00\n📞 Telefon: +998 71 000-00-00",
        "thinking": "⏳ O'ylayapman...",
        "choose_lang": "Tilni tanlang / Выберите язык:",
        "lang_set": "✅ Til o'zbekchaga o'zgartirildi.",
        "voice_heard": "🎤 Siz aytdingiz: {text}",
    },
}

SYSTEM_PROMPT = """Ты — умный помощник жилого комплекса Family Park в Самарканде, Узбекистан.
Ты помогаешь жителям с вопросами об оплате, заявках на ремонт, информации о ЖК.
ВАЖНО: отвечай на том же языке, на котором написал пользователь (русский или узбекский). Если пользователь пишет на узбекском — отвечай на узбекском латиницей.
Отвечай кратко и вежливо. Если вопрос не по теме ЖК — вежливо перенаправь.
Информация о ЖК: адрес — Самарканд, телефон — +998 71 000-00-00, режим работы 9:00-18:00."""


def get_or_create_resident(telegram_id: int, full_name: str):
    result = supabase.table("residents").select("*").eq("telegram_id", telegram_id).execute()
    if result.data:
        return result.data[0]
    new_resident = supabase.table("residents").insert({
        "telegram_id": telegram_id,
        "full_name": full_name,
        "balance": 450000,
        "language": "ru"
    }).execute()
    return new_resident.data[0]


def get_lang(resident):
    return resident.get("language") or "ru"


def main_menu(lang):
    t = TEXTS[lang]
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t["btn_balance"]), KeyboardButton(text=t["btn_repair"])],
            [KeyboardButton(text=t["btn_requests"]), KeyboardButton(text=t["btn_operator"])],
            [KeyboardButton(text=t["btn_info"]), KeyboardButton(text=t["btn_lang"])],
        ],
        resize_keyboard=True
    )


def lang_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru"),
         InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data="lang_uz")]
    ])


# Определяем, на какую кнопку нажали, независимо от языка
def match_button(text, key):
    return text in (TEXTS["ru"][key], TEXTS["uz"][key])


@dp.message(Command("start"))
async def start(message: types.Message):
    resident = get_or_create_resident(message.from_user.id, message.from_user.full_name)
    lang = get_lang(resident)
    t = TEXTS[lang]
    await message.answer(
        t["welcome"].format(name=message.from_user.first_name),
        reply_markup=main_menu(lang)
    )


@dp.callback_query(lambda c: c.data in ("lang_ru", "lang_uz"))
async def set_language(callback: types.CallbackQuery):
    new_lang = "ru" if callback.data == "lang_ru" else "uz"
    supabase.table("residents").update({"language": new_lang}).eq("telegram_id", callback.from_user.id).execute()
    t = TEXTS[new_lang]
    await callback.message.answer(t["lang_set"], reply_markup=main_menu(new_lang))
    await callback.answer()


@dp.message(lambda m: m.text and match_button(m.text, "btn_lang"))
async def change_language(message: types.Message):
    resident = get_or_create_resident(message.from_user.id, message.from_user.full_name)
    lang = get_lang(resident)
    await message.answer(TEXTS[lang]["choose_lang"], reply_markup=lang_keyboard())


@dp.message(lambda m: m.text and match_button(m.text, "btn_balance"))
async def balance(message: types.Message):
    resident = get_or_create_resident(message.from_user.id, message.from_user.full_name)
    lang = get_lang(resident)
    await message.answer(TEXTS[lang]["balance"].format(balance=resident['balance']))


@dp.message(lambda m: m.text and match_button(m.text, "btn_repair"))
async def repair(message: types.Message):
    resident = get_or_create_resident(message.from_user.id, message.from_user.full_name)
    lang = get_lang(resident)
    await message.answer(TEXTS[lang]["repair"])


@dp.message(lambda m: m.text and match_button(m.text, "btn_requests"))
async def my_requests(message: types.Message):
    resident = get_or_create_resident(message.from_user.id, message.from_user.full_name)
    lang = get_lang(resident)
    result = supabase.table("requests").select("*").eq("telegram_id", message.from_user.id).execute()
    if not result.data:
        await message.answer(TEXTS[lang]["no_requests"])
        return
    text = TEXTS[lang]["requests_title"]
    for r in result.data:
        text += f"• {r['description']} — {r['status']}\n"
    await message.answer(text)


@dp.message(lambda m: m.text and match_button(m.text, "btn_operator"))
async def operator(message: types.Message):
    resident = get_or_create_resident(message.from_user.id, message.from_user.full_name)
    lang = get_lang(resident)
    await message.answer(TEXTS[lang]["operator"])


@dp.message(lambda m: m.text and match_button(m.text, "btn_info"))
async def info(message: types.Message):
    resident = get_or_create_resident(message.from_user.id, message.from_user.full_name)
    lang = get_lang(resident)
    await message.answer(TEXTS[lang]["info"])


@dp.message(F.voice)
async def voice_message(message: types.Message):
    resident = get_or_create_resident(message.from_user.id, message.from_user.full_name)
    lang = get_lang(resident)
    await message.answer(TEXTS[lang]["thinking"])
    try:
        # Скачиваем голосовой файл
        file = await bot.get_file(message.voice.file_id)
        file_path = f"/tmp/voice_{message.from_user.id}.ogg"
        await bot.download_file(file.file_path, file_path)

        # Распознаём речь через Whisper (Groq)
        with open(file_path, "rb") as audio:
            transcription = groq_client.audio.transcriptions.create(
                file=(file_path, audio.read()),
                model="whisper-large-v3",
            )
        text = transcription.text.strip()
        os.remove(file_path)

        if not text:
            await message.answer("🎤 ...", reply_markup=main_menu(lang))
            return

        # Показываем распознанный текст
        await message.answer(TEXTS[lang]["voice_heard"].format(text=text))

        # Если похоже на заявку на ремонт — сохраняем
        repair_keywords = ["сломал", "течет", "не работает", "ремонт", "сломан", "протекает",
                           "buzildi", "ishlamayapti", "oqyapti", "ta'mir", "sindi"]
        if any(word in text.lower() for word in repair_keywords):
            supabase.table("requests").insert({
                "telegram_id": message.from_user.id,
                "description": text,
                "status": "new"
            }).execute()

        # Отвечаем через ИИ
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text}
            ],
            max_tokens=500
        )
        await message.answer(response.choices[0].message.content, reply_markup=main_menu(lang))
    except Exception as e:
        await message.answer(f"Ошибка: {str(e)}", reply_markup=main_menu(lang))
        
    @dp.message(F.text)
    async def ai_response(message: types.Message):
     resident = get_or_create_resident(message.from_user.id, message.from_user.full_name)
     lang = get_lang(resident)

    repair_keywords = ["сломал", "течет", "не работает", "ремонт", "сломан", "протекает",
                       "buzildi", "ishlamayapti", "oqyapti", "ta'mir", "sindi"]
    if message.text and any(word in message.text.lower() for word in repair_keywords):
        supabase.table("requests").insert({
            "telegram_id": message.from_user.id,
            "description": message.text,
            "status": "new"
        }).execute()

    await message.answer(TEXTS[lang]["thinking"])
    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": message.text}
            ],
            max_tokens=500
        )
        await message.answer(response.choices[0].message.content, reply_markup=main_menu(lang))
    except Exception as e:
        await message.answer(f"Ошибка: {str(e)}", reply_markup=main_menu(lang))


async def main():
    print("✅ Бот с ИИ, базой данных и поддержкой 2 языков запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())