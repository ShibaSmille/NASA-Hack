from flask import Flask, request, jsonify
from flask_cors import CORS
from geopy.geocoders import Nominatim
import requests
import pandas as pd
import numpy as np
import datetime 
import traceback # Додаємо для детального логування помилок

# --- 1. ДОПОМІЖНІ ФУНКЦІЇ ---

def get_coordinates(city_name):
    """Перетворює назву міста на (широту, довготу) за допомогою Nominatim."""
    geolocator = Nominatim(user_agent="nasa-project-hackathon")
    
    try:
        # Встановлюємо тайм-аут
        location = geolocator.geocode(city_name, timeout=10)
        
        if location:
            return location.latitude, location.longitude
        else:
            return None, None
    except Exception as e:
        print(f"Помилка геокодування: {e}")
        return None, None

def fetch_nasa_data(latitude, longitude, date_of_year_str):
    """
    Імітує запит історичних даних з NASA, генеруючи 20 років даних.
    """
    
    num_years = 20 # Кількість років для аналізу
    print(f"NASA Logics: Імітація запиту MERRA-2/Data Rods для: {latitude}, {longitude} на дату {date_of_year_str} (Генерація {num_years} років даних)")
    
    # 1. Визначення місяця для сезонності
    try:
        target_date = datetime.datetime.strptime(date_of_year_str, '%Y-%m-%d')
        month = target_date.month
    except ValueError:
        month = 7 
    
    # 2. Розрахунок базової температури (залежить від широти та сезону)
    
    # Сезонний зсув
    if month in [12, 1, 2]: # Зима
        seasonal_shift = -15 
        rain_base = 5 
        wind_base = 10 
    elif month in [6, 7, 8]: # Літо
        seasonal_shift = 15 
        rain_base = 10 
        wind_base = 5 
    elif month in [3, 4, 5]: # Весна
        seasonal_shift = 0
        rain_base = 8
        wind_base = 7
    else: # Осінь (9, 10, 11)
        seasonal_shift = 5
        rain_base = 7
        wind_base = 8
        
    # Базова температура залежить від широти (Kyiv ~50, Miami ~25)
    base_latitude_temp = 25 - (abs(latitude) * 0.5) 
    
    # Фінальна базова температура
    base_temp = base_latitude_temp + seasonal_shift
    
    # Вологість: вища для прибережних районів
    humidity_adjustment = 0
    if abs(longitude) < 30 or abs(longitude) > 100:
         humidity_adjustment = 5
         
    # 3. Генерація даних (імітація 20 років)
    np.random.seed(42) 

    data = {
        'Temp_C': np.round(np.random.normal(base_temp, 5, num_years), 1),
        'Rain_mm': np.round(np.random.normal(rain_base, 4, num_years).clip(min=0), 1),
        'Humidity_RH': np.round(np.random.uniform(70 + humidity_adjustment, 95, num_years), 1),
        'Wind_m_s': np.round(np.random.normal(wind_base, 3, num_years).clip(min=0), 1)
    }
    
    return pd.DataFrame(data)

# --- 2. ЛОГІКА РОЗРАХУНКУ ЙМОВІРНОСТЕЙ ---

def calculate_probability(df):
    """Рассчитывает вероятность плохих условий по точным критериям пользователя."""
    
    total_days = df.shape[0] 
    
    # КРИТЕРІЇ "ПОГАНОГО ДНЯ" 
    
    # 1. Пляж (Beach): Bad: T < 24°C АБО Опади > 5 мм
    bad_beach_count = df[(df['Temp_C'] < 24) | (df['Rain_mm'] > 5)].shape[0]
    prob_beach_bad = round((bad_beach_count / total_days) * 100)
    
    # 2. Лижі (Skiing): Bad: T > 0°C
    bad_skiing_count = df[df['Temp_C'] > 0].shape[0]
    prob_skiing_bad = round((bad_skiing_count / total_days) * 100)
    
    # 3. Туризм (Hiking): Bad: T > 30°C АБО Опади > 10 мм
    bad_hiking_count = df[(df['Temp_C'] > 30) | (df['Rain_mm'] > 10)].shape[0]
    prob_hiking_bad = round((bad_hiking_count / total_days) * 100)
    
    # 4. Риболовля (Fishing): Bad: Опади > 10 мм АБО W > 10 м/с
    bad_fishing_count = df[(df['Rain_mm'] > 10) | (df['Wind_m_s'] > 10)].shape[0]
    prob_fishing_bad = round((bad_fishing_count / total_days) * 100)
    
    # 5. Фестиваль (Festival): Bad: Опади > 5 мм АБО T > 32°C
    bad_festival_count = df[(df['Rain_mm'] > 5) | (df['Temp_C'] > 32)].shape[0]
    prob_festival_bad = round((bad_festival_count / total_days) * 100)
    
    return {
        "very_hot": f"{prob_beach_bad}%",          
        "very_wet": f"{prob_skiing_bad}%",         
        "very_uncomfortable": f"{prob_festival_bad}%", 
        "hiking_prob": f"{prob_hiking_bad}%", 
        "fishing_prob": f"{prob_fishing_bad}%",
    }

# --- 3. НАЛАШТУВАННЯ FLASK ---

app = Flask(__name__)
# Дозволяємо CORS для з'єднання з фронтендом
CORS(app) 

@app.route('/calculate_risk', methods=['POST'])
def get_weather_odds():
    try:
        data = request.json
        location = data.get('location')
        date_of_year = data.get('date')
        
        if not location or not date_of_year:
            return jsonify({"error": "Missing location or date"}), 400

        # 1. ГЕОКОДУВАННЯ (Отримання координат)
        latitude, longitude = get_coordinates(location)
        
        if not latitude or not longitude:
            return jsonify({"error": f"Could not find coordinates for {location}. Try again."}), 404

        # 2. ОТРИМАННЯ ТА ОБРОБКА ДАНИХ NASA
        historical_df = fetch_nasa_data(latitude, longitude, date_of_year)
        
        if historical_df.empty:
            return jsonify({"error": "Data calculation failed. The historical dataset was empty, preventing risk probability calculation."}), 500

        # 3. РОЗРАХУНОК ЙМОВІРНОСТЕЙ
        probabilities = calculate_probability(historical_df)

        # 4. ФОРМУВАННЯ ВІДПОВІДІ
        raw_data_sample = historical_df.head(20).to_dict('records') # 20 рядків

        response = {
            "query": f"Запит для {location} (Широта: {latitude:.2f}, Довгота: {longitude:.2f}) на дату {date_of_year}",
            "probabilities": probabilities,
            "raw_data_sample": raw_data_sample
        }
        
        return jsonify(response)
    
    except Exception as e:
        # Логуємо повний трасування стека для діагностики в консолі
        print("--- UNEXPECTED SERVER ERROR ---")
        print(traceback.format_exc())
        print("-------------------------------")
        
        # Повертаємо деталі помилки 500
        return jsonify({
            "error": "Критична помилка сервера при обробці даних. Перевірте консоль Python для деталей.",
            "details": str(e)
        }), 500

# ЦЕЙ БЛОК ДЛЯ ПРЯМОГО ЗАПУСКУ ФАЙЛУ З КОМАНДНОГО РЯДКА
if __name__ == '__main__':
    # Flask буде запущено на стандартному порту 5000
    app.run(debug=True) 