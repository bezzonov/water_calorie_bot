import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import re

from config import TELEGRAM_TOKEN
from utils import (
    get_weather, calculate_water_goal, calculate_calorie_goal,
    get_food_calories, get_workout_calories
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot setup
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# User data storage
users = {}

# FSM States
class ProfileStates(StatesGroup):
    waiting_weight = State()
    waiting_height = State()
    waiting_age = State()
    waiting_activity = State()
    waiting_city = State()

class FoodStates(StatesGroup):
    waiting_grams = State()

@dp.message(Command('start'))
async def start_handler(message: Message):
    user_id = message.from_user.id
    if user_id not in users:
        users[user_id] = {}

    await message.answer(
        "💧🤖 Добро пожаловать в трекер воды и калорий!\n\n"
        "Доступные команды:\n"
        "/set_profile - настроить профиль\n"
        "/log_water <л> - залить воду\n"
        "/log_food <продукт> - записать еду\n"
        "/log_workout <тип> <мин> - тренировка\n"
        "/check_progress - прогресс\n"
        "/help - помощь"
    )

@dp.message(Command('help'))
async def help_handler(message: Message):
    await message.answer(
        "📋 Помощь:\n\n"
        "• /set_profile - вес, рост, возраст, активность, город\n"
        "• /log_water 500 - выпить 500 мл воды\n"
        "• /log_food банан - съесть банан\n"
        "• /log_workout бег 30 - пробежать 30 мин\n"
        "• /check_progress - текущий прогресс"
    )

@dp.message(Command('set_profile'))
async def set_profile_start(message: Message, state: FSMContext):
    user_id = message.from_user.id
    users[user_id] = users.get(user_id, {})
    await state.set_state(ProfileStates.waiting_weight)
    await message.answer("⚖️ Введите ваш вес (в кг):")

@dp.message(StateFilter(ProfileStates.waiting_weight))
async def process_weight(message: Message, state: FSMContext):
    user_id = message.from_user.id
    try:
        weight = float(message.text)
        users[user_id]['weight'] = weight
        await state.set_state(ProfileStates.waiting_height)
        await message.answer(f"✅ Вес: {weight} кг\n📏 Введите рост (в см):")
    except ValueError:
        await message.answer("❌ Введите число! Попробуйте снова:")

@dp.message(StateFilter(ProfileStates.waiting_height))
async def process_height(message: Message, state: FSMContext):
    user_id = message.from_user.id
    try:
        height = float(message.text)
        users[user_id]['height'] = height
        await state.set_state(ProfileStates.waiting_age)
        await message.answer(f"✅ Рост: {height} см\n🎂 Введите возраст:")
    except ValueError:
        await message.answer("❌ Введите число! Попробуйте снова:")

@dp.message(StateFilter(ProfileStates.waiting_age))
async def process_age(message: Message, state: FSMContext):
    user_id = message.from_user.id
    try:
        age = int(message.text)
        users[user_id]['age'] = age
        await state.set_state(ProfileStates.waiting_activity)
        await message.answer(f"✅ Возраст: {age} лет\n🏃‍♂️ Минут активности в день:")
    except ValueError:
        await message.answer("❌ Введите число! Попробуйте снова:")

@dp.message(StateFilter(ProfileStates.waiting_activity))
async def process_activity(message: Message, state: FSMContext):
    user_id = message.from_user.id
    try:
        activity = int(message.text)
        users[user_id]['activity'] = activity
        users[user_id]['city'] = users[user_id].get('city', 'Moscow')

        # Update goals
        temp = await get_weather(users[user_id]['city'])
        users[user_id]['temperature'] = temp or 20
        users[user_id]['water_goal'] = calculate_water_goal(users[user_id])
        users[user_id]['calorie_goal'] = calculate_calorie_goal(users[user_id])

        # Reset daily counters
        users[user_id]['logged_water'] = 0
        users[user_id]['logged_calories'] = 0
        users[user_id]['burned_calories'] = 0

        await state.clear()
        await message.answer(
            f"✅ Профиль сохранен!\n\n"
            f"💧 Норма воды: {users[user_id]['water_goal']:.0f} мл\n"
            f"🔥 Норма калорий: {users[user_id]['calorie_goal']:.0f} ккал\n"
            f"🌡️ Температура: {temp or 20}°C"
        )
    except ValueError:
        await message.answer("❌ Введите число! Попробуйте снова:")

@dp.message(Command('log_water'))
async def log_water(message: Message):
    user_id = message.from_user.id
    if user_id not in users or 'water_goal' not in users[user_id]:
        return await message.answer("❌ Сначала настройте профиль: /set_profile")

    match = re.match(r'/log_water\s+(\d+)', message.text)
    if not match:
        return await message.answer("❌ Формат: /log_water 500")

    amount = float(match.group(1))
    users[user_id]['logged_water'] += amount

    remaining = max(0, users[user_id]['water_goal'] - users[user_id]['logged_water'])
    percent = min(100, (users[user_id]['logged_water'] / users[user_id]['water_goal']) * 100)

    await message.answer(
        f"💧 Записано {amount} мл\n"
        f"📊 Выпито: {users[user_id]['logged_water']:.0f} мл / {users[user_id]['water_goal']:.0f} мл\n"
        f"💦 Осталось: {remaining:.0f} мл ({percent:.0f}%)"
    )

@dp.message(Command('log_food'))
async def log_food_start(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id not in users:
        return await message.answer("❌ Сначала настройте профиль: /set_profile")

    match = re.match(r'/log_food\s+(.+)', message.text)
    if not match:
        return await message.answer("❌ Формат: /log_food банан")

    product = match.group(1).strip()
    food_data = get_food_calories(product)

    await state.update_data(product=product, food_data=food_data)
    await state.set_state(FoodStates.waiting_grams)
    await message.answer(
        f"🍌 {food_data['name']} — {food_data['cal']} ккал/100г\n"
        f"📊 Сколько грамм вы съели?"
    )

@dp.message(StateFilter(FoodStates.waiting_grams))
async def process_food_grams(message: Message, state: FSMContext):
    user_id = message.from_user.id
    data = await state.get_data()

    try:
        grams = float(message.text)
        cal_per_100 = data['food_data']['cal']
        calories = (grams / 100) * cal_per_100

        users[user_id]['logged_calories'] += calories

        await state.clear()
        await message.answer(
            f"✅ Записано: {calories:.1f} ккал от {grams}г {data['product']}\n"
            f"📈 Всего съедено: {users[user_id]['logged_calories']:.0f} ккал"
        )
    except ValueError:
        await message.answer("❌ Введите число грамм!")

@dp.message(Command('log_workout'))
async def log_workout(message: Message):
    user_id = message.from_user.id
    if user_id not in users:
        return await message.answer("❌ Сначала настройте профиль: /set_profile")

    match = re.match(r'/log_workout\s+(\w+)\s+(\d+)', message.text)
    if not match:
        return await message.answer("❌ Формат: /log_workout бег 30")

    workout_type = match.group(1)
    minutes = int(match.group(2))
    weight = users[user_id].get('weight', 70)

    calories, water_extra = get_workout_calories(workout_type, minutes, weight)
    users[user_id]['burned_calories'] += calories

    await message.answer(
        f"🏃‍♂️ {workout_type.capitalize()} {minutes} мин\n"
        f"🔥 Сожжено: {calories} ккал\n"
        f"💧 Выпейте дополнительно {water_extra} мл воды!\n"
        f"📊 Всего сожжено: {users[user_id]['burned_calories']:.0f} ккал"
    )

@dp.message(Command('check_progress'))
async def check_progress(message: Message):
    user_id = message.from_user.id
    if user_id not in users or 'water_goal' not in users[user_id]:
        return await message.answer("❌ Сначала настройте профиль: /set_profile")

    user = users[user_id]

    water_progress = min(100, (user['logged_water'] / user['water_goal']) * 100)
    cal_consumed_progress = min(100, (user['logged_calories'] / user['calorie_goal']) * 100)
    net_calories = user['logged_calories'] - user['burned_calories']

    text = f"""📊 Прогресс за день:

💧 Вода:
• Выпито: {user['logged_water']:.0f}/{user['water_goal']:.0f} мл
• Осталось: {max(0, user['water_goal']-user['logged_water']):.0f} мл
• Прогресс: {water_progress:.0f}%

🔥 Калории:
• Потреблено: {user['logged_calories']:.0f}/{user['calorie_goal']:.0f} ккал
• Сожжено: {user['burned_calories']:.0f} ккал
• Баланс: {net_calories:.0f} ккал ({cal_consumed_progress:.0f}%)"""

    await message.answer(text)

async def main():
    logger.info("Starting bot...")
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
