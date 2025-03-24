from flask import Flask, request, render_template
import joblib
import numpy as np
import pandas as pd

app = Flask(__name__)

# Load the trained models
model_pm10 = joblib.load("best_rf_pm10.pkl")
model_pm25 = joblib.load("best_rf_pm25.pkl")

# Define feature names (EXCLUDING Wind)
MODEL_FEATURES = ['CO(GT)', 'NOx(GT)', 'NMHC(GT)', 'C6H6(GT)', 'PT08.S1(CO)', 'PT08.S2(NMHC)', 'PT08.S3(NOx)',  
                  'NO2(GT)', 'PT08.S4(NO2)', 'PT08.S5(O3)', 'T', 'RH', 'AH', 'Year', 'Month', 'Day', 'Hour']

# Features for input form (INCLUDING Wind for AQI)
INPUT_FEATURES = MODEL_FEATURES + ['Wind']

# AQI Breakpoints
breakpoints = {
    "PM2.5": [(0, 12, 0, 50), (12.1, 35.4, 51, 100), (35.5, 55.4, 101, 150), (55.5, 150.4, 151, 200),
              (150.5, 250.4, 201, 300), (250.5, 350.4, 301, 400), (350.5, 500.4, 401, 500)],
    
    "PM10": [(0, 54, 0, 50), (55, 154, 51, 100), (155, 254, 101, 150), (255, 354, 151, 200),
             (355, 424, 201, 300), (425, 504, 301, 400), (505, 604, 401, 500)]
}

# Function to calculate AQI
def calculate_aqi(concentration, pollutant):
    for c_low, c_high, i_low, i_high in breakpoints[pollutant]:
        if c_low <= concentration <= c_high:
            aqi = ((i_high - i_low) / (c_high - c_low)) * (concentration - c_low) + i_low
            return round(aqi)
    return 500  # Max AQI if beyond range

# Function to adjust AQI based on environmental factors
def adjust_aqi(aqi_pm25, aqi_pm10, RH, Temp, Wind):
    final_aqi = max(aqi_pm25, aqi_pm10)

    if RH > 80:
        final_aqi *= 1.1  
    elif RH < 30:
        final_aqi *= 0.9  

    if Temp > 40 or Temp < 0:
        final_aqi *= 1.05  

    if Wind > 15:
        final_aqi *= 0.8  

    return round(min(final_aqi, 500))  

# Function to classify AQI
def classify_air_quality(aqi):
    if aqi <= 50:
        return "Good 😊 ✅"
    elif aqi <= 100:
        return "Moderate 😐 ☀️"
    elif aqi <= 150:
        return "Unhealthy for Sensitive Groups 🤧 🌫️"
    elif aqi <= 200:
        return "Unhealthy 😷 🚨"
    elif aqi <= 300:
        return "Very Unhealthy 🤢 ☠️"
    else:
        return "Hazardous ☠️ 🚫"

@app.route("/", methods=["GET", "POST"])
def predict():
    if request.method == "POST":
        try:
            # Get all input values
            input_values = {feature: float(request.form[feature]) for feature in INPUT_FEATURES}

            # Create DataFrame for model (EXCLUDE Wind)
            model_input_df = pd.DataFrame([[input_values[feature] for feature in MODEL_FEATURES]], columns=MODEL_FEATURES)

            # Predict PM10 and PM2.5
            pm10_prediction = model_pm10.predict(model_input_df)[0]
            pm25_prediction = model_pm25.predict(model_input_df)[0]

            # Calculate AQI for PM10 and PM2.5
            aqi_pm25 = calculate_aqi(pm25_prediction, "PM2.5")
            aqi_pm10 = calculate_aqi(pm10_prediction, "PM10")

            # Extract RH, Temp, and Wind for AQI adjustment
            RH, Temp, Wind = input_values["RH"], input_values["T"], input_values["Wind"]

            # Adjust AQI
            final_aqi = adjust_aqi(aqi_pm25, aqi_pm10, RH, Temp, Wind)
            aqi_category = classify_air_quality(final_aqi)

            return render_template("index.html", prediction_pm10=pm10_prediction, prediction_pm25=pm25_prediction, 
                                   aqi=final_aqi, aqi_category=aqi_category)
        except Exception as e:
            return f"Error: {e}"

    return render_template("index.html", prediction_pm10=None, prediction_pm25=None, aqi=None, aqi_category=None)

if __name__ == "__main__":
    app.run(debug=True)
