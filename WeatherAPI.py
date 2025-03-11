import openmeteo_requests
import requests_cache
import pandas as pd
from retry_requests import retry
import statistics
import requests
import random
import json
import time
import numpy as np

# Setup the Open-Meteo API client with cache and retry on error
cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
openmeteo = openmeteo_requests.Client(session=retry_session)

def get_coordinates_from_zip(zip_code, country_code="US"):
	"""Convert a zip/postal code to latitude and longitude coordinates."""
	try:
		# For US zip codes, ensure it's formatted correctly
		if country_code == "US" and len(zip_code) > 0:
			# Strip to just digits for US zip codes
			zip_code = ''.join(filter(str.isdigit, zip_code))
			# Truncate to 5 digits if longer
			if len(zip_code) > 5:
				zip_code = zip_code[:5]
			# Pad with zeros if shorter
			while len(zip_code) < 5:
				zip_code = '0' + zip_code
		
		# Only proceed with NWS API for US zip codes
		if country_code == "US":
			try:
				# First, try the NWS API to get the coordinates
				print(f"Looking up zip code: {zip_code} using NWS API")
				
				# Set a custom user agent as required by NWS API
				headers = {
					'User-Agent': 'WeatherClothingAdvisor/1.0 (your-email@example.com)',
					'Accept': 'application/geo+json'
				}
				
				# Use the NWS API to get the coordinates for the zip code
				nws_url = f"https://api.weather.gov/points/search?query={zip_code}"
				response = requests.get(nws_url, headers=headers)
				
				if response.status_code == 200:
					data = response.json()
					print(f"NWS API Response: {data}")
					
					# Check if we got any results
					if 'features' in data and len(data['features']) > 0:
						# Get the first feature (most relevant match)
						feature = data['features'][0]
						
						# Extract coordinates (they're in [longitude, latitude] order in GeoJSON)
						coordinates = feature['geometry']['coordinates']
						longitude = coordinates[0]
						latitude = coordinates[1]
						
						# Extract location name from properties
						properties = feature['properties']
						city = properties.get('name', 'Unknown Location')
						state = properties.get('state', '')
						
						location_name = city
						if state:
							location_name += f", {state}"
						
						return {
							"latitude": latitude,
							"longitude": longitude,
							"name": location_name,
							"country": "United States",
							"success": True
						}
			except Exception as nws_error:
				print(f"NWS API lookup failed: {str(nws_error)}")
				# Continue to the next method
			
			# If NWS API fails, try the Open-Meteo geocoding API
			try:
				print(f"Trying Open-Meteo API for zip code: {zip_code}")
				url = f"https://geocoding-api.open-meteo.com/v1/search?postal_code={zip_code}&country_code={country_code}"
				response = requests.get(url)
				
				# Check if the request was successful
				if response.status_code == 200:
					data = response.json()
					print(f"Open-Meteo API Response: {data}")
					
					if "results" in data and len(data["results"]) > 0:
						result = data["results"][0]
						return {
							"latitude": result["latitude"],
							"longitude": result["longitude"],
							"name": result.get("name", "Unknown Location"),
							"country": result.get("country", "United States"),
							"success": True
						}
			except Exception as api_error:
				print(f"Open-Meteo API lookup failed: {str(api_error)}")
				# Continue to the fallback mechanism
			
			# If both APIs fail, check our hardcoded list for common zip codes
			us_zip_mapping = {
				# Major cities
				"10001": {"lat": 40.7500, "lon": -73.9967, "name": "New York", "country": "United States"},
				"90210": {"lat": 34.0901, "lon": -118.4065, "name": "Beverly Hills", "country": "United States"},
				"60601": {"lat": 41.8855, "lon": -87.6221, "name": "Chicago", "country": "United States"},
				"33101": {"lat": 25.7751, "lon": -80.1947, "name": "Miami", "country": "United States"},
				"98101": {"lat": 47.6101, "lon": -122.3420, "name": "Seattle", "country": "United States"},
				"19104": {"lat": 39.9523, "lon": -75.1638, "name": "Philadelphia", "country": "United States"},
				"19002": {"lat": 40.1526, "lon": -75.2155, "name": "Ambler, PA", "country": "United States"}
				# Reduced list for brevity - will fall back to region-based approximation for others
			}
			
			# Check if we have a hardcoded mapping for this zip code
			if zip_code in us_zip_mapping:
				mapping = us_zip_mapping[zip_code]
				return {
					"latitude": mapping["lat"],
					"longitude": mapping["lon"],
					"name": mapping["name"],
					"country": mapping["country"],
					"success": True
				}
			
			# Fallback: approximate based on first 3 digits of zip code
			# Get the first 3 digits of the zip code (the prefix)
			zip_prefix = zip_code[:3]
			
			# Map of zip code prefixes to approximate regions
			zip_prefix_mapping = {
				# Northeast
				"010": {"lat": 42.1085, "lon": -72.5829, "name": "Springfield, MA area", "country": "United States"},
				"020": {"lat": 42.3601, "lon": -71.0589, "name": "Boston, MA area", "country": "United States"},
				"100": {"lat": 40.7128, "lon": -74.0060, "name": "New York, NY area", "country": "United States"},
				"190": {"lat": 39.9526, "lon": -75.1652, "name": "Philadelphia, PA area", "country": "United States"},
				"200": {"lat": 38.9072, "lon": -77.0369, "name": "Washington, DC area", "country": "United States"},
				
				# South
				"300": {"lat": 33.7490, "lon": -84.3880, "name": "Atlanta, GA area", "country": "United States"},
				"330": {"lat": 28.5383, "lon": -81.3792, "name": "Orlando, FL area", "country": "United States"},
				"370": {"lat": 36.1627, "lon": -86.7816, "name": "Nashville, TN area", "country": "United States"},
				
				# Midwest
				"430": {"lat": 39.9612, "lon": -82.9988, "name": "Columbus, OH area", "country": "United States"},
				"480": {"lat": 42.3314, "lon": -83.0458, "name": "Detroit, MI area", "country": "United States"},
				"530": {"lat": 43.0389, "lon": -87.9065, "name": "Milwaukee, WI area", "country": "United States"},
				"600": {"lat": 41.8781, "lon": -87.6298, "name": "Chicago, IL area", "country": "United States"},
				
				# West
				"750": {"lat": 32.7767, "lon": -96.7970, "name": "Dallas, TX area", "country": "United States"},
				"770": {"lat": 29.7604, "lon": -95.3698, "name": "Houston, TX area", "country": "United States"},
				"800": {"lat": 39.7392, "lon": -104.9903, "name": "Denver, CO area", "country": "United States"},
				"850": {"lat": 33.4484, "lon": -112.0740, "name": "Phoenix, AZ area", "country": "United States"},
				"900": {"lat": 34.0522, "lon": -118.2437, "name": "Los Angeles, CA area", "country": "United States"},
				"940": {"lat": 37.7749, "lon": -122.4194, "name": "San Francisco, CA area", "country": "United States"},
				"980": {"lat": 47.6062, "lon": -122.3321, "name": "Seattle, WA area", "country": "United States"}
			}
			
			# Try to find a match for the first 3 digits
			for prefix in zip_prefix_mapping:
				if zip_prefix.startswith(prefix):
					mapping = zip_prefix_mapping[prefix]
					# Add a small random offset to make it look like a specific location
					lat_offset = (random.random() - 0.5) * 0.1
					lon_offset = (random.random() - 0.5) * 0.1
					return {
						"latitude": mapping["lat"] + lat_offset,
						"longitude": mapping["lon"] + lon_offset,
						"name": f"Near {mapping['name']} (approximated)",
						"country": mapping["country"],
						"success": True
					}
		
		# For non-US countries or if all lookups failed
		return {
			"success": False,
			"error": f"Zip code '{zip_code}' not found. Please try another zip code or use coordinates."
		}
	except Exception as e:
		import traceback
		print(f"Error in zip code lookup: {str(e)}")
		print(traceback.format_exc())
		return {
			"success": False,
			"error": f"Error processing request: {str(e)}"
		}

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
	
	# Round temperature values to 1 decimal place
	hourly_data["temperature"] = np.round(hourly_temperature[:24], 1)
	hourly_data["precipitation"] = np.round(hourly_precipitation[:24], 2)
	hourly_data["windspeed"] = np.round(hourly_windspeed[:24], 1)
	
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