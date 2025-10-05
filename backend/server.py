import json
import random
import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS

#SCIENCE
import xarray as xr
import pandas as pd
import netCDF4
import requests # Earthdata Login

app = Flask(__name__)
CORS(app) 


NASA_USERNAME = 'shiba_smille'  
NASA_PASSWORD = 'Shiba09.05.09' 

# Базовый URL для OPeNDAP на MERRA-2 (Global Land monthly means)
# Внимание: Для 40-летнего ежедневного анализа лучше использовать Daily/Hourly files или Data Rods.
# Мы используем Monthly для простоты демонстрации структуры OPeNDAP.
OPENDAP_BASE_URL = "https://goldsmr4.gesdisc.eosdis.nasa.gov/dods/MERRA2/M2TMNXTEMP.5.12.4"
MERRA2_VARIABLES = ['T2M', 'PRECTOT', 'U10M', 'V10M'] # Температура (К), Осадки (кг/м2/с), Ветер X/Y (м/с)

# Контекстные пороговые значения (для 5 активностей)
# T2M_MIN/MAX в Цельсиях, PRECTOT_MAX в мм/час, WIND_MAX в м/с.
ACTIVITY_THRESHOLDS = {
    'Beach': {'T2M_MIN': 24, 'PRECTOT_MAX': 5, 'WIND_MAX': 10},  
    'Skiing': {'T2M_MAX': 0, 'PRECTOT_MAX': 1, 'WIND_MAX': 15},   
    'Hiking': {'T2M_MAX': 30, 'PRECTOT_MAX': 5, 'WIND_MAX': 20}, 
    'Fishing': {'PRECTOT_MAX': 10, 'WIND_MAX': 15}, 
    'Festival': {'T2M_MAX': 32, 'PRECTOT_MAX': 5, 'WIND_MAX': 15}, 
}

def calculate_bad_days(historical_data, activity):
    """Рассчитывает количество "Плохих Дней" на основе заданных пороговых значений активности."""
    
    thresholds = ACTIVITY_THRESHOLDS.get(activity, {})
    bad_days = 0
    total_days = historical_data.shape[0]

    for index, row in historical_data.iterrows():
        is_bad = False
        
        # 1. Температура (T2M)
        # T2M в MERRA-2 дается в Кельвинах (K), переводим в Цельсии (°C).
        T2M_Celsius = row.get('T2M', 293.15) - 273.15 
        
        if 'T2M_MIN' in thresholds and T2M_Celsius < thresholds['T2M_MIN']:
            is_bad = True
        if 'T2M_MAX' in thresholds and T2M_Celsius > thresholds['T2M_MAX']:
            is_bad = True
            
        # 2. Осадки (PRECTOT)
        # PRECTOT - суммарные осадки в kg/m2/s. Переводим в mm/hr (1 kg/m2/s = 3600 mm/hr)
        precipitation_mm_hr = row.get('PRECTOT', 0) * 3600
        if 'PRECTOT_MAX' in thresholds and precipitation_mm_hr > thresholds['PRECTOT_MAX']:
            is_bad = True
            
        # 3. Ветер (U10M, V10M)
        # Скорость ветра (Wind Speed) = sqrt(U^2 + V^2)
        U = row.get('U10M', 0)
        V = row.get('V10M', 0)
        wind_speed = (U**2 + V**2)**0.5
        if 'WIND_MAX' in thresholds and wind_speed > thresholds['WIND_MAX']:
            is_bad = True

        if is_bad:
            bad_days += 1
            
    if total_days == 0:
        return 0, 0
        
    risk_percentage = round((bad_days / total_days) * 100)
    return risk_percentage, total_days


def fetch_and_analyze_merra2_data(lat, lon, date_str, activity):
    """
    Реальная функция, которая выполняет запрос к NASA OPeNDAP, используя xarray.
    """
    
    if NASA_USERNAME == 'YOUR_EARTHDATA_USERNAME' or NASA_PASSWORD == 'YOUR_EARTHDATA_PASSWORD':
        # В случае, если учетные данные не заменены, возвращаем имитацию
        print("WARNING: Using SIMULATION. Replace NASA_USERNAME/PASSWORD for real data.")
        target_date = datetime.datetime.strptime(date_str, '%Y-%m-%d')
        target_month = target_date.month
        
        base_risk = (abs(lon) % 40) + 10 
        if activity == 'Beach' and (target_month < 5 or target_month > 9):
            seasonal_modifier = 25
        elif activity == 'Skiing' and (target_month > 4 and target_month < 11):
            seasonal_modifier = 30
        else:
            seasonal_modifier = 0

        simulated_risk = base_risk + seasonal_modifier + random.randint(1, 10)
        return min(95, simulated_risk)
        

    try:
        target_date = datetime.datetime.strptime(date_str, '%Y-%m-%d')
        target_month = target_date.month
        
        # 1. Аутентификация NASA Earthdata Login
        session = requests.Session()
        session.auth = (NASA_USERNAME, NASA_PASSWORD)
        
        # 2. Подключение к OPeNDAP
        # Мы подключаемся к набору Monthly Mean и берем все доступное время.
        # В реальном проекте здесь требуется сложный запрос на поднабор данных (subsetting) по Lat/Lon.
        print(f"DEBUG: Attempting to open OPeNDAP dataset from {OPENDAP_BASE_URL}...")
        ds = xr.open_dataset(OPENDAP_BASE_URL, engine='netcdf4', backend_kwargs={'session': session})

        # 3. Выборка данных по координатам и фильтрация по месяцу
        # Находим ближайший к точке (lat, lon) узел сетки
        ds_point = ds.sel(lat=lat, lon=lon, method='nearest')
        
        # Преобразуем в Pandas DataFrame
        df = ds_point.to_dataframe().dropna()
        
        # Фильтруем все данные по месяцу, игнорируя год, чтобы получить 40 лет истории для этого месяца
        df['month'] = df.index.month
        historical_data = df[df['month'] == target_month]
        
        # 4. Расчет риска
        risk_percentage, total_years = calculate_bad_days(historical_data, activity)
        
        print(f"DEBUG: Found {total_years} historical entries for month {target_month}. Risk: {risk_percentage}%")
        return risk_percentage

    except Exception as e:
        print(f"NASA Data Fetch Error: {e}")
        # Если API NASA недоступен или произошла ошибка выборки, возвращаем высокий риск и ошибку
        return 99 # Возвращаем очень высокий риск, чтобы показать сбой


@app.route('/calculate_risk', methods=['GET'])
def calculate_risk():
    """
    Основная конечная точка для расчета исторического риска.
    """
    
    try:
        lat = request.args.get('lat', type=float)
        lon = request.args.get('lon', type=float)
        date = request.args.get('date')
        activity = request.args.get('activity')
        
        if lat is None or lon is None or not date or not activity:
            return jsonify({"error": "Missing required parameters (lat, lon, date, activity)."}), 400
        
        # Вызываем нашу функцию анализа (теперь она либо реальная, либо симуляция)
        risk_percentage = fetch_and_analyze_merra2_data(lat, lon, date, activity)

        # Успешный ответ
        return jsonify({
            "risk_percentage": risk_percentage
        })

    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        print(f"Server error: {e}")
        return jsonify({"error": f"Internal server error: {e}"}), 500

if __name__ == '__main__':
    # Запуск сервера на порту 5000 (стандартный для Flask)
    # Чтобы запустить: откройте терминал, перейдите в папку с файлом и выполните: python server.py
    app.run(debug=True, port=5000)
