import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
OPENWEATHER_API_KEY = os.getenv('OPENWEATHER_API_KEY')

OPENWEATHER_URL = "http://api.openweathermap.org/data/2.5/weather"
OPENFOODFACTS_URL = "https://world.openfoodfacts.org/api/v0/product/{barcode}.json"
