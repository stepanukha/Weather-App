import openmeteo_requests
import requests_cache
import pandas as pd
from retry_requests import retry
import statistics

# Setup the Open-Meteo API client with cache and retry on error
cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
openmeteo = openmeteo_requests.Client(session=retry_session)

def get_weather_data(latitude, longitude):
	# Make sure all required weather variables are listed here
	url = "https://api.open-meteo.com/v1/forecast"
	params = {
		"latitude": latitude,
		"longitude": longitude,
		"hourly": ["temperature_2m", "precipitation", "windspeed_10m"],
		"temperature_unit": "fahrenheit",
		"forecast_days": 1
	}
	responses = openmeteo.weather_api(url, params=params)
	
	# Process first location
	response = responses[0]
	
	# Process hourly data
	hourly = response.Hourly()
	hourly_temperature = hourly.Variables(0).ValuesAsNumpy()
	hourly_precipitation = hourly.Variables(1).ValuesAsNumpy()
	hourly_windspeed = hourly.Variables(2).ValuesAsNumpy()
	
	# Create a dataframe with the next 24 hours
	hourly_data = {"date": pd.date_range(
		start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
		end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
		freq=pd.Timedelta(seconds=hourly.Interval()),
		inclusive="left"
	)[:24]}
	
	hourly_data["temperature"] = hourly_temperature[:24]
	hourly_data["precipitation"] = hourly_precipitation[:24]
	hourly_data["windspeed"] = hourly_windspeed[:24]
	
	return pd.DataFrame(data=hourly_data)

def get_clothing_recommendation(weather_data):
	# Calculate average values for the day
	avg_temp = statistics.mean(weather_data["temperature"])
	max_precip = max(weather_data["precipitation"])
	max_wind = max(weather_data["windspeed"])
	
	# Initialize recommendation
	recommendation = {
		"top": "",
		"bottom": "",
		"outer_layer": "",
		"accessories": []
	}
	
	# Temperature-based recommendations
	if avg_temp > 80:
		recommendation["top"] = "No sleeves, ITS HOT!"
		recommendation["bottom"] = "Shorts or light pants"
	elif avg_temp > 65:
		recommendation["top"] = "Light long-sleeve shirt"
		recommendation["bottom"] = "Light pants or jeans"
	elif avg_temp > 50:
		recommendation["top"] = "Long-sleeve shirt or light sweater"
		recommendation["bottom"] = "Pants or jeans"
		recommendation["outer_layer"] = "Light jacket"
	elif avg_temp > 35:
		recommendation["top"] = "Sweater or fleece"
		recommendation["bottom"] = "Warm pants"
		recommendation["outer_layer"] = "Jacket"
		recommendation["accessories"].append("Light gloves")
	else:
		recommendation["top"] = "Thermal shirt and heavy sweater"
		recommendation["bottom"] = "Thermal pants or heavy jeans"
		recommendation["outer_layer"] = "Heavy winter coat"
		recommendation["accessories"].extend(["Gloves", "Scarf", "Hat"])
	
	# Precipitation-based recommendations
	if max_precip > 0.1:
		recommendation["accessories"].append("Umbrella")
		if "jacket" in recommendation["outer_layer"].lower():
			recommendation["outer_layer"] = "Waterproof " + recommendation["outer_layer"].lower()
		else:
			recommendation["outer_layer"] = "Rain jacket"
	
	# Wind-based recommendations
	if max_wind > 15:
		if not recommendation["outer_layer"]:
			recommendation["outer_layer"] = "Windbreaker"
		recommendation["accessories"].append("Hat (to prevent it from blowing away)")
	
	return recommendation

def display_recommendation(recommendation, weather_data):
	print("\n===== WEATHER SUMMARY =====")
	print(f"Average Temperature: {statistics.mean(weather_data['temperature']):.1f}°F")
	print(f"Max Precipitation: {max(weather_data['precipitation']):.2f} inches")
	print(f"Max Wind Speed: {max(weather_data['windspeed']):.1f} mph")
	
	print("\n===== CLOTHING RECOMMENDATION =====")
	print(f"Top: {recommendation['top']}")
	print(f"Bottom: {recommendation['bottom']}")
	if recommendation['outer_layer']:
		print(f"Outer Layer: {recommendation['outer_layer']}")
	if recommendation['accessories']:
		print(f"Accessories: {', '.join(recommendation['accessories'])}")

def main():
	# Get user location or use default
	try:
		print("Enter your location coordinates (or press Enter for Philadelphia):")
		user_lat = input("Latitude (e.g., 39.9523 for Philadelphia): ")
		user_lon = input("Longitude (e.g., -75.1638 for Philadelphia): ")
		
		latitude = float(user_lat) if user_lat else 39.9523
		longitude = float(user_lon) if user_lon else -75.1638
	except ValueError:
		print("Invalid coordinates. Using Philadelphia as default.")
		latitude = 39.9523
		longitude = -75.1638
	
	print(f"\nFetching weather data for coordinates: {latitude}°N, {longitude}°E...")
	weather_data = get_weather_data(latitude, longitude)
	
	recommendation = get_clothing_recommendation(weather_data)
	display_recommendation(recommendation, weather_data)

if __name__ == "__main__":
	main()