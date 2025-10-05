import datetime
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
import time # Добавляем для реализации механизма повторных попыток (Exponential Backoff)

# --- КОНФИГУРАЦИЯ СЕРВЕРА ---
app = Flask(__name__)
# Включаем CORS для работы с фронтендом
CORS(app) 

# --- ПАРАМЕТРЫ РИСКА И ЛОГИКА РАСЧЕТА ---

# Параметры NASA POWER: T2M (°C), PRECTOT (mm/день), WS2M (м/с)
ACTIVITY_THRESHOLDS = {
    'Beach': {'T2M_MIN': 24, 'PRECTOT_MAX': 5, 'WS2M_MAX': 10},  # Пляж: тепло и мало осадков/ветра
    'Skiing': {'T2M_MAX': 0, 'PRECTOT_MAX': 1, 'WS2M_MAX': 15},   # Лыжи: холодно и почти без дождя
    'Hiking': {'T2M_MAX': 30, 'PRECTOT_MAX': 10, 'WS2M_MAX': 20}, # Поход: не слишком жарко и умеренный ветер/дождь
    'Fishing': {'PRECTOT_MAX': 10, 'WS2M_MAX': 15},               # Рыбалка: мало осадков и умеренный ветер
    'Festival': {'T2M_MAX': 32, 'PRECTOT_MAX': 5, 'WS2M_MAX': 15}, # Фестиваль: не слишком жарко и без ливня
}

def calculate_risk_percentage(historical_data, activity):
    """Рассчитывает процент "Плохих Дней" на основе заданных пороговых значений активности."""
    
    thresholds = ACTIVITY_THRESHOLDS.get(activity, {})
    bad_days = 0
    total_days = len(historical_data)

    if total_days == 0:
        return 0
        
    for row in historical_data:
        is_bad = False
        
        # Получаем данные
        temp = row.get('Temp_C', -999)
        rain = row.get('Rain_mm', -999)
        wind = row.get('Wind_m_s', -999)
        
        # Если данные пропущены (NASA использует -999.00), пропускаем этот год
        if temp < -990 or rain < -990 or wind < -990:
             continue 
        
        # 1. Температура (T2M) - Проверка на слишком холодно/слишком жарко
        if 'T2M_MIN' in thresholds and temp < thresholds['T2M_MIN']:
            is_bad = True
        if 'T2M_MAX' in thresholds and temp > thresholds['T2M_MAX']:
            is_bad = True
            
        # 2. Осадки (PRECTOT) - Проверка на слишком много дождя
        if 'PRECTOT_MAX' in thresholds and rain > thresholds['PRECTOT_MAX']:
            is_bad = True
            
        # 3. Ветер (WS2M) - Проверка на слишком сильный ветер
        if 'WS2M_MAX' in thresholds and wind > thresholds['WS2M_MAX']:
            is_bad = True

        if is_bad:
            bad_days += 1
            
    # Расчет процента
    risk_percentage = round((bad_days / total_days) * 100)
    return risk_percentage

# --- ЗАГРУЗКА ДАННЫХ NASA POWER (с повторными попытками) ---

def fetch_nasa_power_data(lat, lon, month, day, max_retries=3):
    """
    Загружает исторические климатические данные NASA POWER (1984-2023) 
    для заданного дня и месяца с механизмом повторных попыток.
    """
    PARAMETERS = "T2M,PRECTOT,WS2M" 
    # API POWER предоставляет более 40 лет данных (с 1984 по 2023)
    API_URL = f"https://power.larc.nasa.gov/api/temporal/daily/point?parameters={PARAMETERS}&community=AG&longitude={lon}&latitude={lat}&start=19840101&end=20231231&format=JSON"

    print(f"Загрузка данных с NASA POWER API для Lat:{lat}, Lon:{lon}...")
    
    for attempt in range(max_retries):
        try:
            # Используем requests для запроса, авторизация не требуется
            response = requests.get(API_URL, timeout=10) 
            response.raise_for_status() 
            data = response.json()
            
            # Парсинг данных после успешного запроса
            yearly_data = []
            
            if 'properties' not in data or 'parameter' not in data['properties']:
                print("Ошибка: Неожиданная структура данных от NASA API.")
                return None
                
            temp_data = data['properties']['parameter'].get('T2M', {})
            rain_data = data['properties']['parameter'].get('PRECTOT', {})
            wind_data = data['properties']['parameter'].get('WS2M', {})

            for date_str, temp in temp_data.items():
                try:
                    date_obj = datetime.datetime.strptime(date_str, '%Y%m%d')
                except ValueError:
                    continue

                # Фильтруем данные, оставляя только нужный день/месяц за каждый год
                if date_obj.month == month and date_obj.day == day:
                    
                    rain = rain_data.get(date_str, -999.0)
                    wind = wind_data.get(date_str, -999.0)
                    
                    if temp < -990 or rain < -990 or wind < -990:
                        continue 
                    
                    yearly_data.append({
                        "Year": date_obj.year,
                        "Temp_C": temp,
                        "Rain_mm": rain,
                        "Wind_m_s": wind,
                    })
                    
            return yearly_data

        except requests.exceptions.RequestException as e:
            print(f"Попытка {attempt + 1}/{max_retries}: Ошибка во время запроса к NASA API: {e}")
            if attempt < max_retries - 1:
                # Экспоненциальная задержка: 2, 4, 8 секунд
                sleep_time = 2 ** (attempt + 1)
                time.sleep(sleep_time)
                continue
            return None # Вернуть None после последней неудачной попытки

        except Exception as e:
            print(f"Неожиданная ошибка при обработке данных NASA: {e}")
            return None


# --- FLASK ROUTE: ОСНОВНАЯ ТОЧКА ВХОДА ---

@app.route('/calculate_risk', methods=['POST'])
def calculate_risk():
    """
    Основная конечная точка для расчета исторического риска.
    Принимает Координаты (lat, lon), Дату (date) и Активность (activity) в формате JSON.
    """
    
    try:
        data = request.json
        lat = data.get('lat', None)
        lon = data.get('lon', None)
        date_str = data.get('date', '')
        activity = data.get('activity', '')

        # 1. Проверка входящих данных
        if lat is None or lon is None or not date_str or not activity:
             return jsonify({"error": "В JSON-запросе отсутствуют обязательные параметры (lat, lon, date, activity)."}), 400

        # 2. Парсинг Даты
        try:
            dt = datetime.datetime.strptime(date_str, '%Y-%m-%d')
            month = dt.month
            day = dt.day
        except ValueError:
            return jsonify({"error": "Неверный формат даты. Используйте ГГГГ-ММ-ДД."}), 400

        # 3. Загрузка данных NASA POWER (настоящий запрос)
        historical_data = fetch_nasa_power_data(lat, lon, month, day)

        if historical_data is None or len(historical_data) < 20: 
            return jsonify({"error": "Не удалось загрузить или обработать достаточно исторических данных NASA POWER. Убедитесь, что местоположение находится на суше и повторите попытку."}), 500

        # 4. Расчет Риска
        risk_percentage = calculate_risk_percentage(historical_data, activity)
        
        # 5. Успешный ответ
        return jsonify({
            "query": f"Координаты: {lat:.2f}, {lon:.2f}, Дата: {date_str}, Активность: {activity}",
            "risk_percentage": risk_percentage,
            "total_years_analyzed": len(historical_data),
            "source_link": "https://power.larc.nasa.gov/"
        })

    except Exception as e:
        print(f"Критическая ошибка сервера: {e}")
        return jsonify({"error": f"Критическая внутренняя ошибка сервера: {e}"}), 500

if __name__ == '__main__':
    # В реальном развертывании используйте gunicorn или waitress
    app.run(debug=True, port=5000)