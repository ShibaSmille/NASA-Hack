import os
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime

# Ініціалізація Flask та CORS
app = Flask(__name__)
# Дозволяємо CORS для взаємодії з фронтендом
CORS(app)

# --- ГЕОКОДУВАННЯ: КОНВЕРТАЦІЯ МІСТА В КООРДИНАТИ ---

# 1. Фіксовані координати (для швидкого доступу до популярних міст)
PRESET_COORDS = {
    "kyiv": {"lat": 50.45, "lon": 30.52, "name": "Kyiv, Ukraine"},
    "london": {"lat": 51.5, "lon": -0.12, "name": "London, UK"},
    "miami": {"lat": 25.76, "lon": -80.19, "name": "Miami, USA"},
    "tokyo": {"lat": 35.68, "lon": 139.69, "name": "Tokyo, Japan"},
    "sydney": {"lat": -33.86, "lon": 151.2, "name": "Sydney, Australia"},
}

def get_coords_from_nominatim(location_name):
    """Використовує Nominatim API для перетворення назви міста на координати."""
    NOMINATIM_API_URL = "https://nominatim.openstreetmap.org/search"
    
    # Nominatim вимагає встановлення User-Agent
    headers = {'User-Agent': 'NASA_SpaceApps_Challenge_App/1.0 (contact@example.com)'} 
    params = {
        'q': location_name,
        'format': 'json', # Просимо JSON
        'limit': 1        # Беремо лише найкращий результат
    }
    
    print(f"Запит до Nominatim: {location_name}")
    
    try:
        response = requests.get(NOMINATIM_API_URL, params=params, headers=headers, timeout=5)
        response.raise_for_status()
        
        results = response.json()
        
        if results and len(results) > 0:
            first_result = results[0]
            return {
                "lat": float(first_result['lat']),
                "lon": float(first_result['lon']),
                "name": first_result['display_name'] 
            }
        else:
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"Помилка під час запиту до Nominatim API (з'єднання): {e}")
        return None

def get_coords(location_name):
    """Отримує координати, спочатку перевіряючи пресети, потім Nominatim."""
    name_lower = location_name.lower()
    
    # 1. Перевірка пресетів (швидкий кеш)
    preset_coords = PRESET_COORDS.get(name_lower, None)
    if preset_coords:
        return preset_coords
    
    # 2. Виклик Nominatim для довільного міста
    return get_coords_from_nominatim(location_name)

# --- ОСНОВНА ЛОГІКА: ДОСТУП ДО API NASA POWER ---
def fetch_nasa_power_data(lat, lon, month, day):
    """
    Завантажує історичні кліматичні дані NASA POWER (на базі MERRA-2).
    """
    PARAMETERS = "T2M,RH2M,PRECTOT,WS2M" 
    
    API_URL = f"https://power.larc.nasa.gov/api/temporal/daily/point?parameters={PARAMETERS}&community=AG&longitude={lon}&latitude={lat}&start=19840101&end=20231231&format=JSON"

    print(f"Запит до NASA POWER API: {API_URL}")
    
    try:
        response = requests.get(API_URL, timeout=10) 
        response.raise_for_status() 
        
        if not response.text:
            print("Помилка: Відповідь від NASA API порожня.")
            return None
            
        data = response.json()
        
    except requests.exceptions.RequestException as e:
        print(f"Помилка під час запиту до NASA API (з'єднання, таймаут, DNS): {e}")
        return None
    except requests.exceptions.JSONDecodeError as e:
        print(f"ПОМИЛКА ДЕКОДУВАННЯ JSON! Сервер NASA повернув недійсний формат.")
        print(f"Отримана відповідь (перші 200 символів): {response.text[:200]}...")
        return None

    # Обробка та фільтрація даних
    yearly_data = []
    
    if 'properties' not in data or 'parameter' not in data['properties']:
        print("Помилка: Несподівана структура даних від NASA API.")
        return None
        
    temp_data = data['properties']['parameter'].get('T2M', {})
    rain_data = data['properties']['parameter'].get('PRECTOT', {})
    humidity_data = data['properties']['parameter'].get('RH2M', {})
    wind_data = data['properties']['parameter'].get('WS2M', {})

    # Ітеруємо по датах, щоб витягнути тільки потрібний нам день і місяць
    for date_str, temp in temp_data.items():
        if date_str.endswith(f"{month:02d}{day:02d}"):
            # Перевіряємо, чи немає пропущених значень (-999.0)
            rain = rain_data.get(date_str, -999.0)
            humidity = humidity_data.get(date_str, -999.0)
            wind = wind_data.get(date_str, -999.0)
            
            # Якщо будь-яке значення є пропущеним, пропускаємо цей рік
            if temp < -990 or rain < -990 or humidity < -990 or wind < -990:
                 continue 
            
            year = int(date_str[:4])
            
            yearly_data.append({
                "Year": year,
                "Temp_C": temp,
                "Rain_mm": rain,
                "Humidity_RH": humidity,
                "Wind_m_s": wind,
            })
            
    return yearly_data

def calculate_risks(data):
    """Розраховує ризики на основі реальних історичних даних."""
    if not data:
        return {k: "N/A" for k in ["very_hot", "very_wet", "hiking_prob", "fishing_prob", "very_uncomfortable"]}
    
    total_years = len(data)
    
    if total_years == 0:
        return {k: "0%" for k in ["very_hot", "very_wet", "hiking_prob", "fishing_prob", "very_uncomfortable"]}

    bad_beach, bad_ski, bad_hiking, bad_fishing, bad_festival = 0, 0, 0, 0, 0
    
    for row in data:
        temp = row['Temp_C']
        rain = row['Rain_mm']
        wind = row['Wind_m_s']
        
        # 1. Пляж: T < 24°C АБО Rain > 5 мм
        if temp < 24 or rain > 5:
            bad_beach += 1
        
        # 2. Лижі: T > 0°C (ризик відсутності снігу)
        if temp > 0:
            bad_ski += 1
        
        # 3. Туризм: T > 30°C АБО Rain > 10 мм
        if temp > 30 or rain > 10:
            bad_hiking += 1

        # 4. Риболовля: Rain > 10 мм АБО Wind > 10 м/с
        if rain > 10 or wind > 10:
            bad_fishing += 1
        
        # 5. Фестиваль: Rain > 5 мм АБО T > 32°C 
        if rain > 5 or temp > 32:
            bad_festival += 1

    # Розрахунок відсотків
    probabilities = {
        "very_hot": f"{round((bad_beach / total_years) * 100)}%",
        "very_wet": f"{round((bad_ski / total_years) * 100)}%",
        "hiking_prob": f"{round((bad_hiking / total_years) * 100)}%",
        "fishing_prob": f"{round((bad_fishing / total_years) * 100)}%",
        "very_uncomfortable": f"{round((bad_festival / total_years) * 100)}%"
    }
    
    return probabilities

# --- FLASK ROUTE: ОСНОВНА ТОЧКА ВХОДУ ---
@app.route('/api/weather-odds', methods=['POST'])
def weather_odds():
    data = request.json
    location_name = data.get('location', '')
    date_str = data.get('date', '')

    # 1. Конвертація Міста в Координати (тепер Nominatim)
    coords = get_coords(location_name)
    if not coords:
        # Оновлене повідомлення про помилку
        return jsonify({"error": "Місто не знайдено. Переконайтеся, що ви ввели повну назву міста (наприклад, 'Kyiv', 'Paris' або 'Lviv')."}), 400

    # 2. Парсинг Дати
    try:
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        month = dt.month
        day = dt.day
    except ValueError:
        return jsonify({"error": "Невірний формат дати. Використовуйте РРРР-ММ-ДД."}), 400

    # 3. Завантаження даних NASA POWER
    historical_data = fetch_nasa_power_data(coords['lat'], coords['lon'], month, day)

    if historical_data is None:
        return jsonify({"error": "Помилка завантаження або обробки даних від NASA POWER API. Дивіться лог сервера для деталей."}), 500

    # 4. Розрахунок Ризиків
    probabilities = calculate_risks(historical_data)

    # 5. Підготовка відповіді
    response_data = {
        "query": f"Місто: {coords['name']}, Дата: {month:02d}-{day:02d}",
        "probabilities": probabilities,
        "raw_data_sample": historical_data[:10],
        # АТРИБУЦІЯ: Посилання на джерело даних NASA
        "source_link": "https://power.larc.nasa.gov/"
    }

    return jsonify(response_data)

if __name__ == '__main__':
    # Flask запускається через 'flask run', але це для локального тестування:
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
