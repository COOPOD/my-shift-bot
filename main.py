import asyncio
import os
from datetime import datetime
from aiohttp import web
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

API_TOKEN = os.getenv("BOT_TOKEN", "8671644137:AAG0_X_8SnpT2t7CsWbw3aA0ERxP2C8RDQs").strip()

dp = Dispatcher()

class RateState(StatesGroup):
    waiting_for_rates = State()

user_data = {}

def get_user_data(user_id: int):
    if user_id not in user_data:
        user_data[user_id] = {
            "day_rate": 1000.0,
            "night_rate": 1200.0,
            "history": []
        }
    return user_data[user_id]

def calculate_stats(data: dict):
    day_count = sum(1 for item in data["history"] if item["type"] == "day")
    night_count = sum(1 for item in data["history"] if item["type"] == "night")
    day_total = day_count * data["day_rate"]
    night_total = night_count * data["night_rate"]
    return day_count, night_count, day_total, night_total, day_total + night_total

def generate_report(data: dict) -> str:
    day_cnt, night_cnt, day_sum, night_sum, total = calculate_stats(data)
    return (
        "📊 <b>Текущий расчет за месяц:</b>\n\n"
        f"☀️ <b>Дневные смены:</b> {day_cnt} шт. × {data['day_rate']:.0f} = {day_sum:.2f}\n"
        f"🌙 <b>Ночные смены:</b> {night_cnt} шт. × {data['night_rate']:.0f} = {night_sum:.2f}\n"
        f"➖➖➖➖➖➖➖➖➖➖\n"
        f"💰 <b>ИТОГО К ВЫПЛАТЕ: {total:.2f}</b>\n\n"
        "💡 <i>Пишите «день» или «ночь», чтобы добавить смену.</i>\n"
        "⚙️ <i>Команда /set_rates — изменить тарифы.</i>\n"
        "↩️ <i>Команда /cancel — отменить последнюю смену.</i>\n"
        "🔄 <i>Команда /reset — сбросить месяц.</i>"
    )

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(generate_report(get_user_data(message.from_user.id)), parse_mode="HTML")

@dp.message(Command("set_rates"))
async def cmd_set_rates(message: types.Message, state: FSMContext):
    await message.answer("Введите новые тарифы через пробел (например: <code>1000 1300</code>):", parse_mode="HTML")
    await state.set_state(RateState.waiting_for_rates)

@dp.message(RateState.waiting_for_rates)
async def process_rates(message: types.Message, state: FSMContext):
    try:
        parts = message.text.split()
        data = get_user_data(message.from_user.id)
        data["day_rate"], data["night_rate"] = float(parts[0]), float(parts[1])
        await state.clear()
        await message.answer(f"✅ Тарифы обновлены!\n☀️ День: {parts[0]}\n🌙 Ночь: {parts[1]}")
        await message.answer(generate_report(data), parse_mode="HTML")
    except Exception:
        await message.answer("❌ Введите два числа через пробел, например: <code>1000 1200</code>", parse_mode="HTML")

@dp.message(F.text.lower().in_({"день", "ночь", "day", "night"}))
async def add_shift(message: types.Message):
    data = get_user_data(message.from_user.id)
    shift_type = "day" if message.text.lower() in ["день", "day"] else "night"
    now_str = datetime.now().strftime("%d.%m")
    data["history"].append({"type": shift_type, "date": now_str})
    label = "☀️ Дневная" if shift_type == "day" else "🌙 Ночная"
    await message.answer(f"✅ Засчитана {label} смена ({now_str})")
    await message.answer(generate_report(data), parse_mode="HTML")

@dp.message(Command("cancel"))
async def cmd_cancel(message: types.Message):
    data = get_user_data(message.from_user.id)
    if data["history"]:
        removed = data["history"].pop()
        label = "☀️ Дневная" if removed["type"] == "day" else "🌙 Ночная"
        await message.answer(f"🗑 Удалена смена: {label} ({removed['date']})")
    else:
        await message.answer("Список смен пуст.")
    await message.answer(generate_report(data), parse_mode="HTML")

@dp.message(Command("reset"))
async def cmd_reset(message: types.Message):
    data = get_user_data(message.from_user.id)
    data["history"] = []
    await message.answer("🔄 Счетчик сброшен!")
    await message.answer(generate_report(data), parse_mode="HTML")

async def handle(request):
    return web.Response(text="Bot is running!")

async def main():
    bot = Bot(token=API_TOKEN)
    
    try:
        await bot.delete_webhook(drop_pending_updates=True)
    except Exception:
        pass
        
    print("🚀 Бот успешно запущен!")
    
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
