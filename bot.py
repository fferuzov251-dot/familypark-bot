import asyncio
import os
from groq import Groq
from supabase import create_client
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
groq_client = Groq(api_key=GROQ_API_KEY)
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ==== СПИСОК АДМИНОВ (telegram_id сотрудников ЖК) ====
# Чтобы добавить сотрудника — впиши его id через запятую: [1361035231, 123456789]
ADMINS = [1361035231]

def is_admin(telegram_id: int) -> bool:
    return telegram_id in ADMINS

# ==== КНОПКИ АДМИН-МЕНЮ (текст) ====
ADM_BTN_NEW = "🆕 Новые заявки"
ADM_BTN_PROGRESS = "🔧 В работе"

# ==== СОСТОЯНИЯ ====
class Registration(StatesGroup):
    waiting_apartment = State()
    waiting_phone = State()

class Repair(StatesGroup):
    waiting_description = State()

# ==== СТАТУСЫ ЗАЯВОК (для показа жителю) ====
STATUS_TEXT = {
    "ru": {"new": "🆕 Новая", "in_progress": "🔧 В работе", "done": "✅ Выполнено"},
    "uz": {"new": "🆕 Yangi", "in_progress": "🔧 Jarayonda", "done": "✅ Bajarildi"},
}

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
        "repair_ask": "🔧 Опишите вашу проблему одним сообщением (что и где сломалось).\n\nДля отмены напишите: отмена",
        "repair_done": "✅ Заявка №{id} принята!\n🏠 Квартира: {apt}\n📝 {desc}\n\nМы свяжемся с вами в ближайшее время.",
        "repair_cancel": "❌ Заявка отменена.",
        "no_requests": "📋 У вас пока нет заявок.",
        "requests_title": "📋 Ваши заявки:\n\n",
        "operator": "📞 Соединяю вас с оператором...\nВремя ожидания: ~5 минут\n\nИли позвоните: +998 71 000-00-00",
        "info": "🏘️ Family Park\n\n📍 Адрес: г. Самарканд\n🕐 Режим работы: 9:00 - 18:00\n📞 Телефон: +998 71 000-00-00",
        "thinking": "⏳ Думаю...",
        "choose_lang": "Выберите язык / Tilni tanlang:",
        "lang_set": "✅ Язык изменён на русский.",
        "voice_heard": "🎤 Вы сказали: {text}",
        "ask_apartment": "📝 Регистрация. Введите номер вашей квартиры (только цифры).\n\nДля отмены напишите: отмена",
        "ask_phone": "📱 Введите ваш номер телефона (например +998 90 123-45-67):",
        "reg_done": "✅ Регистрация завершена! Квартира {apt}. Теперь вам доступны баланс и заявки.",
        "apt_taken": "⚠️ Эта квартира уже зарегистрирована другим пользователем. Если это ошибка — обратитесь к оператору.",
        "apt_invalid": "⚠️ Введите корректный номер квартиры (только цифры).",
        "need_reg": "🔒 Для этого нужна регистрация.\n\n📝 Введите номер вашей квартиры (только цифры).\nДля отмены напишите: отмена",
        "reg_cancel": "❌ Регистрация отменена.",
        # уведомление жителю при смене статуса
        "status_changed": "🔔 Статус вашей заявки №{id} изменён:\n{status}",
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
        "repair_ask": "🔧 Muammoyingizni bitta xabarda yozing (nima va qayerda buzilgan).\n\nBekor qilish uchun yozing: bekor",
        "repair_done": "✅ Ariza №{id} qabul qilindi!\n🏠 Kvartira: {apt}\n📝 {desc}\n\nTez orada siz bilan bog'lanamiz.",
        "repair_cancel": "❌ Ariza bekor qilindi.",
        "no_requests": "📋 Sizda hozircha arizalar yo'q.",
        "requests_title": "📋 Sizning arizalaringiz:\n\n",
        "operator": "📞 Sizni operator bilan bog'layapman...\nKutish vaqti: ~5 daqiqa\n\nYoki qo'ng'iroq qiling: +998 71 000-00-00",
        "info": "🏘️ Family Park\n\n📍 Manzil: Samarqand sh.\n🕐 Ish vaqti: 9:00 - 18:00\n📞 Telefon: +998 71 000-00-00",
        "thinking": "⏳ O'ylayapman...",
        "choose_lang": "Tilni tanlang / Выберите язык:",
        "lang_set": "✅ Til o'zbekchaga o'zgartirildi.",
        "voice_heard": "🎤 Siz aytdingiz: {text}",
        "ask_apartment": "📝 Ro'yxatdan o'tish. Kvartirangiz raqamini kiriting (faqat raqam).\n\nBekor qilish uchun yozing: bekor",
        "ask_phone": "📱 Telefon raqamingizni kiriting (masalan +998 90 123-45-67):",
        "reg_done": "✅ Ro'yxatdan o'tish yakunlandi! Kvartira {apt}. Endi sizga balans va arizalar mavjud.",
        "apt_taken": "⚠️ Bu kvartira boshqa foydalanuvchi tomonidan ro'yxatdan o'tkazilgan. Agar bu xato bo'lsa — operatorga murojaat qiling.",
        "apt_invalid": "⚠️ To'g'ri kvartira raqamini kiriting (faqat raqam).",
        "need_reg": "🔒 Buning uchun ro'yxatdan o'tish kerak.\n\n📝 Kvartirangiz raqamini kiriting (faqat raqam).\nBekor qilish uchun yozing: bekor",
        "reg_cancel": "❌ Ro'yxatdan o'tish bekor qilindi.",
        "status_changed": "🔔 Sizning №{id} arizangiz holati o'zgardi:\n{status}",
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


def is_registered(resident):
    return bool(resident.get("apartment_number"))


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


def admin_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=ADM_BTN_NEW), KeyboardButton(text=ADM_BTN_PROGRESS)],
        ],
        resize_keyboard=True
    )


def lang_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru"),
         InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data="lang_uz")]
    ])


def match_button(text, key):
    return text in (TEXTS["ru"][key], TEXTS["uz"][key])


# ==== КЛАВИАТУРА АДМИНА ДЛЯ ОДНОЙ ЗАЯВКИ ====
# new: обе кнопки; in_progress: только "Выполнено"
def admin_request_keyboard(req_id, status):
    if status == "new":
        rows = [[
            InlineKeyboardButton(text="🔧 В работе", callback_data=f"adm_progress_{req_id}"),
            InlineKeyboardButton(text="✅ Выполнено", callback_data=f"adm_done_{req_id}")
        ]]
    elif status == "in_progress":
        rows = [[
            InlineKeyboardButton(text="✅ Выполнено", callback_data=f"adm_done_{req_id}")
        ]]
    else:
        rows = []
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ==== ПОКАЗ СПИСКА ЗАЯВОК АДМИНУ (по статусу) ====
async def show_admin_requests(message, status):
    result = supabase.table("requests").select("*").eq("status", status).order("id").execute()
    status_name = "новых" if status == "new" else "в работе"
    if not result.data:
        await message.answer(f"📋 Заявок ({status_name}) нет.", reply_markup=admin_menu())
        return

    await message.answer(f"🛠 Заявки ({status_name}): {len(result.data)}", reply_markup=admin_menu())

    for r in result.data:
        res = supabase.table("residents").select("phone, full_name").eq("telegram_id", r["telegram_id"]).execute()
        phone = res.data[0]["phone"] if res.data else "—"
        name = res.data[0]["full_name"] if res.data else "—"

        text = (
            f"📨 Заявка №{r['id']}\n"
            f"🏠 Квартира: {r.get('apartment_number') or '—'}\n"
            f"👤 {name}\n"
            f"📞 {phone or '—'}\n"
            f"📝 {r['description']}"
        )
        await message.answer(text, reply_markup=admin_request_keyboard(r["id"], r["status"]))


async def ai_reply(message, text, lang):
    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text}
        ],
        max_tokens=500
    )
    await message.answer(response.choices[0].message.content, reply_markup=main_menu(lang))


@dp.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    await state.clear()
    resident = get_or_create_resident(message.from_user.id, message.from_user.full_name)
    lang = get_lang(resident)
    t = TEXTS[lang]
    # Если админ — показываем админское меню
    if is_admin(message.from_user.id):
        await message.answer(
            t["welcome"].format(name=message.from_user.first_name),
            reply_markup=main_menu(lang)
        )
        await message.answer("🛠 Вы вошли как сотрудник. Доступно админ-меню ниже.", reply_markup=admin_menu())
        return
    await message.answer(
        t["welcome"].format(name=message.from_user.first_name),
        reply_markup=main_menu(lang)
    )


# ==== АДМИН-ПАНЕЛЬ ====
@dp.message(Command("admin"))
async def admin_panel(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return  # не админ — молча игнорируем
    await state.clear()
    await message.answer("🛠 Админ-панель. Выберите раздел:", reply_markup=admin_menu())


# Кнопка "Новые заявки"
@dp.message(lambda m: m.text == ADM_BTN_NEW)
async def admin_new(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.clear()
    await show_admin_requests(message, "new")


# Кнопка "В работе"
@dp.message(lambda m: m.text == ADM_BTN_PROGRESS)
async def admin_progress(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.clear()
    await show_admin_requests(message, "in_progress")


@dp.callback_query(lambda c: c.data.startswith("adm_"))
async def admin_change_status(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    # callback_data вида adm_progress_5 или adm_done_5
    parts = callback.data.split("_")
    action = parts[1]          # progress / done
    req_id = int(parts[2])

    new_status = "in_progress" if action == "progress" else "done"

    # Обновляем статус в базе
    supabase.table("requests").update({"status": new_status}).eq("id", req_id).execute()

    # Узнаём, кому принадлежит заявка, чтобы уведомить жителя
    req = supabase.table("requests").select("telegram_id").eq("id", req_id).execute()
    if req.data:
        resident_tg = req.data[0]["telegram_id"]
        res = supabase.table("residents").select("language").eq("telegram_id", resident_tg).execute()
        res_lang = res.data[0]["language"] if res.data else "ru"
        status_label = STATUS_TEXT[res_lang].get(new_status, new_status)
        try:
            await bot.send_message(
                resident_tg,
                TEXTS[res_lang]["status_changed"].format(id=req_id, status=status_label)
            )
        except Exception:
            pass  # если житель заблокировал бота — просто не падаем

    # Обновляем сообщение у админа: меняем текст и кнопки под новый статус
    admin_label = STATUS_TEXT["ru"].get(new_status, new_status)
    await callback.message.edit_text(
        callback.message.text + f"\n\n➡️ Статус: {admin_label}",
        reply_markup=admin_request_keyboard(req_id, new_status)
    )
    await callback.answer("Готово ✅")


@dp.callback_query(lambda c: c.data in ("lang_ru", "lang_uz"))
async def set_language(callback: types.CallbackQuery):
    new_lang = "ru" if callback.data == "lang_ru" else "uz"
    supabase.table("residents").update({"language": new_lang}).eq("telegram_id", callback.from_user.id).execute()
    t = TEXTS[new_lang]
    await callback.message.answer(t["lang_set"], reply_markup=main_menu(new_lang))
    await callback.answer()


# ==== РЕГИСТРАЦИЯ (FSM) ====
@dp.message(Registration.waiting_apartment)
async def reg_apartment(message: types.Message, state: FSMContext):
    resident = get_or_create_resident(message.from_user.id, message.from_user.full_name)
    lang = get_lang(resident)
    apt = (message.text or "").strip()

    if apt.lower() in ("отмена", "bekor", "/cancel"):
        await state.clear()
        await message.answer(TEXTS[lang]["reg_cancel"], reply_markup=main_menu(lang))
        return

    if not apt.isdigit():
        await message.answer(TEXTS[lang]["apt_invalid"])
        return

    existing = supabase.table("residents").select("telegram_id").eq("apartment_number", apt).execute()
    for row in existing.data:
        if row["telegram_id"] != message.from_user.id:
            await state.clear()
            await message.answer(TEXTS[lang]["apt_taken"], reply_markup=main_menu(lang))
            return

    await state.update_data(apartment=apt)
    await state.set_state(Registration.waiting_phone)
    await message.answer(TEXTS[lang]["ask_phone"])


@dp.message(Registration.waiting_phone)
async def reg_phone(message: types.Message, state: FSMContext):
    resident = get_or_create_resident(message.from_user.id, message.from_user.full_name)
    lang = get_lang(resident)
    phone = (message.text or "").strip()

    if phone.lower() in ("отмена", "bekor", "/cancel"):
        await state.clear()
        await message.answer(TEXTS[lang]["reg_cancel"], reply_markup=main_menu(lang))
        return

    data = await state.get_data()
    apt = data.get("apartment")

    supabase.table("residents").update({
        "apartment_number": apt,
        "phone": phone
    }).eq("telegram_id", message.from_user.id).execute()

    await state.clear()
    await message.answer(TEXTS[lang]["reg_done"].format(apt=apt), reply_markup=main_menu(lang))


# ==== ЗАЯВКА НА РЕМОНТ (FSM) ====
@dp.message(Repair.waiting_description)
async def repair_description(message: types.Message, state: FSMContext):
    resident = get_or_create_resident(message.from_user.id, message.from_user.full_name)
    lang = get_lang(resident)
    desc = (message.text or "").strip()

    if desc.lower() in ("отмена", "bekor", "/cancel"):
        await state.clear()
        await message.answer(TEXTS[lang]["repair_cancel"], reply_markup=main_menu(lang))
        return

    apt = resident.get("apartment_number")
    inserted = supabase.table("requests").insert({
        "telegram_id": message.from_user.id,
        "description": desc,
        "status": "new",
        "apartment_number": apt
    }).execute()

    req_id = inserted.data[0]["id"]
    await state.clear()
    await message.answer(
        TEXTS[lang]["repair_done"].format(id=req_id, apt=apt, desc=desc),
        reply_markup=main_menu(lang)
    )

    # Уведомляем админов о новой заявке
    for admin_id in ADMINS:
        try:
            await bot.send_message(
                admin_id,
                f"🆕 Новая заявка №{req_id}\n🏠 Квартира: {apt}\n📝 {desc}\n\nНажмите «🆕 Новые заявки» для обработки."
            )
        except Exception:
            pass


@dp.message(lambda m: m.text and match_button(m.text, "btn_lang"))
async def change_language(message: types.Message):
    resident = get_or_create_resident(message.from_user.id, message.from_user.full_name)
    lang = get_lang(resident)
    await message.answer(TEXTS[lang]["choose_lang"], reply_markup=lang_keyboard())


@dp.message(lambda m: m.text and match_button(m.text, "btn_balance"))
async def balance(message: types.Message, state: FSMContext):
    resident = get_or_create_resident(message.from_user.id, message.from_user.full_name)
    lang = get_lang(resident)
    if not is_registered(resident):
        await state.set_state(Registration.waiting_apartment)
        await message.answer(TEXTS[lang]["need_reg"])
        return
    await message.answer(TEXTS[lang]["balance"].format(balance=resident['balance']))


@dp.message(lambda m: m.text and match_button(m.text, "btn_repair"))
async def repair(message: types.Message, state: FSMContext):
    resident = get_or_create_resident(message.from_user.id, message.from_user.full_name)
    lang = get_lang(resident)
    if not is_registered(resident):
        await state.set_state(Registration.waiting_apartment)
        await message.answer(TEXTS[lang]["need_reg"])
        return
    await state.set_state(Repair.waiting_description)
    await message.answer(TEXTS[lang]["repair_ask"])


@dp.message(lambda m: m.text and match_button(m.text, "btn_requests"))
async def my_requests(message: types.Message, state: FSMContext):
    resident = get_or_create_resident(message.from_user.id, message.from_user.full_name)
    lang = get_lang(resident)
    if not is_registered(resident):
        await state.set_state(Registration.waiting_apartment)
        await message.answer(TEXTS[lang]["need_reg"])
        return
    result = supabase.table("requests").select("*").eq("telegram_id", message.from_user.id).order("id").execute()
    if not result.data:
        await message.answer(TEXTS[lang]["no_requests"])
        return
    text = TEXTS[lang]["requests_title"]
    for r in result.data:
        status = STATUS_TEXT[lang].get(r["status"], r["status"])
        text += f"#{r['id']} — {r['description']}\n{status}\n\n"
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
        file = await bot.get_file(message.voice.file_id)
        file_path = f"/tmp/voice_{message.from_user.id}.ogg"
        await bot.download_file(file.file_path, file_path)

        with open(file_path, "rb") as audio:
            transcription = groq_client.audio.transcriptions.create(
                file=(file_path, audio.read()),
                model="whisper-large-v3",
                language=lang,
            )
        text = transcription.text.strip()
        os.remove(file_path)

        if not text:
            await message.answer("🎤 ...", reply_markup=main_menu(lang))
            return

        await message.answer(TEXTS[lang]["voice_heard"].format(text=text))
        await ai_reply(message, text, lang)
    except Exception as e:
        await message.answer(f"Ошибка: {str(e)}", reply_markup=main_menu(lang))


@dp.message(F.text)
async def ai_response(message: types.Message):
    resident = get_or_create_resident(message.from_user.id, message.from_user.full_name)
    lang = get_lang(resident)
    await message.answer(TEXTS[lang]["thinking"])
    try:
        await ai_reply(message, message.text, lang)
    except Exception as e:
        await message.answer(f"Ошибка: {str(e)}", reply_markup=main_menu(lang))


async def main():
    print("✅ Бот: ИИ, база, 2 языка, голос, регистрация, заявки, админ-меню запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())