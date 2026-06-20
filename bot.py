import asyncio
import os
from groq import Groq
from supabase import create_client
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
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

main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="💰 Мой баланс"), KeyboardButton(text="🔧 Заявка на ремонт")],
        [KeyboardButton(text="📋 Мои заявки"), KeyboardButton(text="📞 Связаться с оператором")],
        [KeyboardButton(text="ℹ️ Информация о ЖК")]
    ],
    resize_keyboard=True
)

SYSTEM_PROMPT = """Ты — умный помощник жилого комплекса Family Park в Самарканде, Узбекистан.
Ты помогаешь жителям с вопросами об оплате, заявках на ремонт, информации о ЖК.
Отвечай кратко, вежливо и по-русски. Если вопрос не по теме ЖК — вежливо перенаправь.
Информация о ЖК: адрес — Самарканд, телефон — +998 71 000-00-00, режим работы 9:00-18:00."""


def get_or_create_resident(telegram_id: int, full_name: str):
    result = supabase.table("residents").select("*").eq("telegram_id", telegram_id).execute()
    if result.data:
        return result.data[0]
    new_resident = supabase.table("residents").insert({
        "telegram_id": telegram_id,
        "full_name": full_name,
        "balance": 450000
    }).execute()
    return new_resident.data[0]


@dp.message(Command("start"))
async def start(message: types.Message):
    get_or_create_resident(message.from_user.id, message.from_user.full_name)
    await message.answer(
        f"👋 Добро пожаловать в Family Park!\n\n"
        f"Здравствуйте, {message.from_user.first_name}!\n"
        f"Я ваш персональный ИИ-помощник. Задайте любой вопрос или выберите пункт меню.",
        reply_markup=main_menu
    )

@dp.message(lambda m: m.text == "💰 Мой баланс")
async def balance(message: types.Message):
    resident = get_or_create_resident(message.from_user.id, message.from_user.full_name)
    await message.answer(f"💰 Ваш текущий баланс: {resident['balance']:,} сум\n📅 Следующий платёж: 1 июля 2026")

@dp.message(lambda m: m.text == "🔧 Заявка на ремонт")
async def repair(message: types.Message):
    await message.answer("🔧 Опишите вашу проблему подробно, и я передам заявку в service-отдел.")

@dp.message(lambda m: m.text == "📋 Мои заявки")
async def my_requests(message: types.Message):
    result = supabase.table("requests").select("*").eq("telegram_id", message.from_user.id).execute()
    if not result.data:
        await message.answer("📋 У вас пока нет заявок.")
        return
    text = "📋 Ваши заявки:\n\n"
    for r in result.data:
        text += f"• {r['description']} — {r['status']}\n"
    await message.answer(text)

@dp.message(lambda m: m.text == "📞 Связаться с оператором")
async def operator(message: types.Message):
    await message.answer("📞 Соединяю вас с оператором...\nВремя ожидания: ~5 минут\n\nИли позвоните: +998 71 000-00-00")

@dp.message(lambda m: m.text == "ℹ️ Информация о ЖК")
async def info(message: types.Message):
    await message.answer("🏘️ Family Park\n\n📍 Адрес: г. Самарканд\n🕐 Режим работы: 9:00 - 18:00\n📞 Телефон: +998 71 000-00-00")

@dp.message()
async def ai_response(message: types.Message):
    get_or_create_resident(message.from_user.id, message.from_user.full_name)
    
    # Если похоже на заявку на ремонт - сохраняем в базу
    repair_keywords = ["сломал", "течет", "не работает", "ремонт", "сломан", "протекает"]
    if any(word in message.text.lower() for word in repair_keywords):
        supabase.table("requests").insert({
            "telegram_id": message.from_user.id,
            "description": message.text,
            "status": "new"
        }).execute()

    await message.answer("⏳ Думаю...")
    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": message.text}
            ],
            max_tokens=500
        )
        await message.answer(response.choices[0].message.content, reply_markup=main_menu)
    except Exception as e:
        await message.answer(f"Ошибка: {str(e)}", reply_markup=main_menu)

async def main():
    print("✅ Бот с ИИ и базой данных запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())