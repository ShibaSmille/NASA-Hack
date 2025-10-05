from flask import Flask, request, jsonify
from flask_cors import CORS # Спілкування з фронтендом
from .nasa_data import calculate_probability 



app = Flask(__name__)
CORS(app) 

@app.route('/api/weather-odds', methods=['POST'])
def get_weather_odds():
    # Дані від фронтенда
    data = request.json
    location = data.get('location')
    date_of_year = data.get('date')
    
    if not location or not date_of_year:
        return jsonify({"error": "Missing location or date"}), 400

    # 2. Здесь будет вызов логики NASA (пока заглушка)
    
    # Текстова відповідь на фронтенд
    response = {
        "query": f"Query for {location} on {date_of_year}",
        "probabilities": {
            "very_hot": "60%",
            "very_wet": "25%",
            "very_uncomfortable": "75%"
        }
    }
    
    return jsonify(response)