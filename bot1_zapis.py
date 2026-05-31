"""
БОТ 1 — Запись к мастеру (барбершоп)
=====================================
Установка: pip install aiogram
Запуск:    python bot1_zapis.py
"""

import asyncio
import logging
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

# ─── НАСТРОЙКИ ────────────────────────────────────────────
BOT_TOKEN = "ВСТАВЬ_ТОКЕН_СЮДА"
ADMIN_ID   = 123456789  # Твой Telegram ID (узнай у @userinfobot)

# ─── УСЛУГИ ───────────────────────────────────────────────
SERVICES = {
    "haircut": {"name": "✂️ Стрижка",        "price": 1000},
    "beard":   {"name": "🪒 Борода",          "price": 700},
    "complex": {"name": "💈 Стрижка + борода","price": 1500},
    "color":   {"name": "🎨 Окрашивание",     "price": 2500},
}

# ─── ВРЕМЯ ЗАПИСИ ─────────────────────────────────────────
TIMES = ["10:00","11:00","12:00","13:00","14:00",
         "15:00","16:00","17:00","18:00","19:00"]

# ─── СОСТОЯНИЯ ────────────────────────────────────────────
class Booking(StatesGroup):
    service = State()
    date    = State()
    time    = State()
    confirm = State()

bot = Bot(token=BOT_TOKEN)
dp  = Dispatcher(storage=MemoryStorage())


# ─── КЛАВИАТУРЫ ───────────────────────────────────────────
def kb_services():
    b = InlineKeyboardBuilder()
    for key, s in SERVICES.items():
        b.button(text=f"{s['name']}  —  {s['price']}₽", callback_data=f"svc_{key}")
    b.adjust(1)
    return b.as_markup()

def kb_dates():
    b = InlineKeyboardBuilder()
    days = ["Пн","Вт","Ср","Чт","Пт","Сб","Вс"]
    for i in range(1, 8):
        d = datetime.now() + timedelta(days=i)
        b.button(text=f"{days[d.weekday()]}  {d.strftime('%d.%m')}", callback_data=f"dt_{d.strftime('%d.%m.%Y')}")
    b.adjust(3)
    return b.as_markup()

def kb_times():
    b = InlineKeyboardBuilder()
    for t in TIMES:
        b.button(text=t, callback_data=f"tm_{t}")
    b.adjust(4)
    return b.as_markup()

def kb_confirm():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить", callback_data="ok")],
        [InlineKeyboardButton(text="❌ Отменить",    callback_data="no")],
    ])


# ─── ХЭНДЛЕРЫ ─────────────────────────────────────────────
@dp.message(Command("start"))
async def start(msg: Message, state: FSMContext):
    await state.clear()
    await msg.answer(
        "👋 Добро пожаловать в барбершоп <b>Острый Клинок</b>!\n\n"
        "Записаться к мастеру — пара кликов 👇\n\n"
        "Выберите услугу:",
        parse_mode="HTML",
        reply_markup=kb_services()
    )
    await state.set_state(Booking.service)


@dp.callback_query(F.data.startswith("svc_"))
async def pick_service(cb: CallbackQuery, state: FSMContext):
    key = cb.data[4:]
    svc = SERVICES[key]
    await state.update_data(svc_key=key, svc_name=svc["name"], svc_price=svc["price"])
    await cb.message.edit_text(
        f"✅ Услуга: <b>{svc['name']}</b>  —  {svc['price']}₽\n\n📅 Выберите дату:",
        parse_mode="HTML", reply_markup=kb_dates()
    )
    await state.set_state(Booking.date)
    await cb.answer()


@dp.callback_query(F.data.startswith("dt_"))
async def pick_date(cb: CallbackQuery, state: FSMContext):
    date = cb.data[3:]
    await state.update_data(date=date)
    await cb.message.edit_text(
        f"✅ Дата: <b>{date}</b>\n\n🕐 Выберите время:",
        parse_mode="HTML", reply_markup=kb_times()
    )
    await state.set_state(Booking.time)
    await cb.answer()


@dp.callback_query(F.data.startswith("tm_"))
async def pick_time(cb: CallbackQuery, state: FSMContext):
    time = cb.data[3:]
    await state.update_data(time=time)
    d = await state.get_data()
    await cb.message.edit_text(
        "📋 <b>Ваша запись:</b>\n\n"
        f"💈 {d['svc_name']}\n"
        f"📅 {d['date']} в {time}\n"
        f"💰 {d['svc_price']}₽\n\n"
        "Всё верно?",
        parse_mode="HTML", reply_markup=kb_confirm()
    )
    await state.set_state(Booking.confirm)
    await cb.answer()


@dp.callback_query(F.data == "ok")
async def confirmed(cb: CallbackQuery, state: FSMContext):
    d    = await state.get_data()
    user = cb.from_user
    await cb.message.edit_text(
        "🎉 <b>Запись подтверждена!</b>\n\n"
        f"💈 {d['svc_name']}\n"
        f"📅 {d['date']} в {d['time']}\n"
        f"💰 {d['svc_price']}₽\n\n"
        "Ждём вас! 🙌 За час придёт напоминание.",
        parse_mode="HTML"
    )
    # Уведомление администратору
    try:
        await bot.send_message(
            ADMIN_ID,
            f"🔔 <b>Новая запись!</b>\n\n"
            f"👤 {user.full_name} (@{user.username or '—'})\n"
            f"💈 {d['svc_name']}\n"
            f"📅 {d['date']} в {d['time']}\n"
            f"💰 {d['svc_price']}₽",
            parse_mode="HTML"
        )
    except Exception:
        pass
    await state.clear()


@dp.callback_query(F.data == "no")
async def cancelled(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await cb.message.edit_text("❌ Запись отменена.\n\nНапиши /start чтобы начать заново.")


# ─── ЗАПУСК ───────────────────────────────────────────────
async def main():
    logging.basicConfig(level=logging.INFO)
    print("✅ Бот записи запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
