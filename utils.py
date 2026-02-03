import aiohttp
import math
from typing import Dict, Optional
from config import OPENWEATHER_API_KEY, OPENWEATHER_URL, OPENFOODFACTS_URL

async def get_weather(city: str) -> Optional[float]:
    """Get current temperature for city"""
    try:
        params = {
            'q': city,
            'appid': OPENWEATHER_API_KEY,
            'units': 'metric'
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(OPENWEATHER_URL, params=params) as resp:
                data = await resp.json()
                if data['cod'] == 200:
                    return data['main']['temp']
    except:
        pass
    return None

def calculate_water_goal(user_data: Dict) -> float:
    """Calculate daily water goal"""
    weight = user_data.get('weight', 70)
    activity = user_data.get('activity', 0)
    temp = user_data.get('temperature', 20)

    base = weight * 30  # ml per kg
    activity_bonus = (activity // 30) * 500
    weather_bonus = 750 if temp > 25 else 0

    return base + activity_bonus + weather_bonus

def calculate_calorie_goal(user_data: Dict) -> float:
    """Harris-Benedict formula for BMR + activity"""
    weight = user_data.get('weight', 70)
    height = user_data.get('height', 170)
    age = user_data.get('age', 30)

    # Simplified Mifflin-St Jeor formula
    if user_data.get('gender', 'male') == 'male':
        bmr = 10 * weight + 6.25 * height - 5 * age + 5
    else:
        bmr = 10 * weight + 6.25 * height - 5 * age - 161

    # Activity multiplier
    activity_mult = {
        0: 1.2, 30: 1.375, 60: 1.55, 90: 1.725
    }
    activity_mins = min(user_data.get('activity', 0), 90)
    mult = activity_mult.get(activity_mins // 30 * 30, 1.2)

    return bmr * mult

def get_food_calories(product_name: str) -> Dict[str, float]:
    """Mock food database - replace with real API"""
    food_db = {
        'банан': {'cal': 89, 'name': 'Банан'},
        'яблоко': {'cal': 52, 'name': 'Яблоко'},
        'курица': {'cal': 165, 'name': 'Куриная грудка'},
        'рис': {'cal': 130, 'name': 'Рис вареный'},
        'овсянка': {'cal': 68, 'name': 'Овсянка на воде'},
        'хлеб': {'cal': 265, 'name': 'Хлеб белый'},
        'молоко': {'cal': 42, 'name': 'Молоко 2.5%'},
    }

    product_lower = product_name.lower()
    for food, data in food_db.items():
        if food in product_lower:
            return data
    return {'cal': 100, 'name': 'Неизвестный продукт'}  # default

def get_workout_calories(workout_type: str, minutes: int, weight: float) -> tuple:
    """Calculate calories burned and water needed"""
    met_values = {
        'бег': 9.0, 'ходьба': 3.8, 'велосипед': 8.0,
        'силовая': 6.0, 'плавание': 7.0, 'йога': 3.0
    }

    met = met_values.get(workout_type.lower(), 5.0)
    calories = met * weight * minutes / 60
    water_extra = (minutes // 30) * 200

    return round(calories), water_extra
