from flask import Flask, render_template, request, jsonify
import WeatherAPI
import numpy as np

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/lookup_zip', methods=['POST'])
def lookup_zip():
    data = request.get_json()
    zip_code = data.get('zip_code', '')
    country_code = data.get('country_code', 'US')
    
    if not zip_code:
        return jsonify({
            'success': False,
            'error': 'No zip code provided'
        })
    
    result = WeatherAPI.get_coordinates_from_zip(zip_code, country_code)
    return jsonify(result)

@app.route('/get_recommendation', methods=['POST'])
def get_recommendation():
    data = request.get_json()
    latitude = data.get('latitude', 39.9523)
    longitude = data.get('longitude', -75.1638)
    
    try:
        # Get weather data and recommendation
        weather_data = WeatherAPI.get_weather_data(latitude, longitude)
        recommendation = WeatherAPI.get_clothing_recommendation(weather_data)
        
        # Convert NumPy values to Python native types and ensure proper rounding
        weather_summary = {
            'avg_temp': float(round(weather_data['temperature'].mean(), 1)),  # Round to 1 decimal place
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