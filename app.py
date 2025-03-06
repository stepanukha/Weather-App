from flask import Flask, render_template, request, jsonify
import WeatherAPI
import numpy as np

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_recommendation', methods=['POST'])
def get_recommendation():
    data = request.get_json()
    latitude = data.get('latitude', 39.9523)
    longitude = data.get('longitude', -75.1638)
    
    try:
        # Get weather data and recommendation
        weather_data = WeatherAPI.get_weather_data(latitude, longitude)
        recommendation = WeatherAPI.get_clothing_recommendation(weather_data)
        
        # Convert NumPy values to Python native types
        weather_summary = {
            'avg_temp': float(round(weather_data['temperature'].mean(), 1)),
            'max_precip': float(round(max(weather_data['precipitation']), 2)),
            'max_wind': float(round(max(weather_data['windspeed']), 1))
        }
        
        # Convert any NumPy arrays in recommendation to lists
        for key, value in recommendation.items():
            if isinstance(value, np.ndarray):
                recommendation[key] = value.tolist()
        
        # Return JSON response
        return jsonify({
            'success': True,
            'weather': weather_summary,
            'recommendation': recommendation
        })
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e)
        })

if __name__ == '__main__':
    app.run(debug=True) 