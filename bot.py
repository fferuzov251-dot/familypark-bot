import asyncio
import os
from groq import Groq
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()
groq_client = Groq(api_key=GROQ_API_KEY)

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

@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer(
        f"👋 Добро пожаловать в Family Park!\n\n"
        f"Здравствуйте, {message.from_user.first_name}!\n"
        f"Я ваш персональный ИИ-помощник. Задайте любой вопрос или выберите пункт меню.",
        reply_markup=main_menu
    )

@dp.message(lambda m: m.text == "💰 Мой баланс")
async def balance(message: types.Message):
    await message.answer("💰 Ваш текущий баланс: 450,000 сум\n📅 Следующий платёж: 1 июля 2026")

@dp.message(lambda m: m.text == "🔧 Заявка на ремонт")
async def repair(message: types.Message):
    await message.answer("🔧 Опишите вашу проблему подробно, и я передам заявку в service-отдел.")

@dp.message(lambda m: m.text == "📋 Мои заявки")
async def my_requests(message: types.Message):
    await message.answer("📋 Ваши активные заявки:\n\n1. Ремонт крана — ✅ Выполнено\n2. Замена лампочки — 🔄 В работе")

@dp.message(lambda m: m.text == "📞 Связаться с оператором")
async def operator(message: types.Message):
    await message.answer("📞 Соединяю вас с оператором...\nВремя ожидания: ~5 минут\n\nИли позвоните: +998 71 000-00-00")

@dp.message(lambda m: m.text == "ℹ️ Информация о ЖК")
async def info(message: types.Message):
    await message.answer("🏘️ Family Park\n\n📍 Адрес: г. Самарканд\n🕐 Режим работы: 9:00 - 18:00\n📞 Телефон: +998 71 000-00-00")

@dp.message()
async def ai_response(message: types.Message):
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
    print("✅ Бот с ИИ (Groq) запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())