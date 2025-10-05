import requests
import pandas as pd
import numpy as np

def calculate_probability(location_str, date_of_year_str):
    """Рассчитывает вероятность экстремальных условий по историческим данным."""
    
    # ПРИМЕР: Здесь должен быть реальный запрос к NASA API (OPeNDAP или Giovanni)
    # URL = "URL для исторических данных о температуре в указанном месте" 
    
    # 1. Загрузка исторических данных 
    # (Представим, что вы получили список температур за 20 лет для этой даты)
    
    # Тестовые данные (имитация 20 лет температур 15 июля):
    historical_temps = [25, 28, 30, 32, 27, 26, 35, 31, 29, 28, 33, 27, 26, 30, 29, 31, 34, 28, 27, 30]
    
    df = pd.DataFrame(historical_temps, columns=['Temp_C'])

    # 2. Определение порогов и вероятностей
    
    # Порог "Очень жарко": Температура выше 32°C
    HOT_THRESHOLD = 32
    
    # Считаем, сколько дней превысили порог
    hot_days_count = df[df['Temp_C'] >= HOT_THRESHOLD].shape[0]
    print 
    # Рассчитываем вероятность (Процент дней)
    total_days = df.shape[0]
    prob_hot = round((hot_days_count / total_days) * 100) # Процент
    
    # 3. Возврат результата
    return {
        "very_hot": f"{prob_hot}%",
        "very_wet": "Тут будет расчет вероятности сильных осадков",
        "very_uncomfortable": "Тут будет расчет по индексу влажности",
    }