# App.py
# Imports
import os
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
from flask import Flask, render_template, request, redirect, url_for, session, jsonify,flash
import pandas as pd
from influxdb_client import InfluxDBClient
import plotly
import plotly.graph_objects as go
import json
from components.PredictionModel import PredictionModel
from dotenv import load_dotenv
from components.login import login_user, logout_user
from flask import session, redirect, url_for
from components.Alert import  SettingsForm, send_email, save_config, load_config, alert_for_predicted_values,check_proactive_status,check_current_status,evaluate_sensor_status
from flask import Flask, render_template, request, redirect, url_for, session
from dotenv import load_dotenv

load_dotenv(override=True)

# Setup InfluxDB connection parameters
INFLUXDB_URL = os.environ.get('INFLUXDB_URL')
INFLUXDB_TOKEN = os.environ.get('INFLUXDB_TOKEN')
INFLUXDB_ORG = os.environ.get('INFLUXDB_ORG')
INFLUXDB_BUCKET = os.environ.get('INFLUXDB_BUCKET')

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY')

# Initialize InfluxDB client
client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
query_api = client.query_api()

# Define the model path and initialize the prediction model using a specific path
MODEL_PATH = os.environ.get('MODEL_PATH')
prediction_model = PredictionModel(MODEL_PATH)

# /send-test-email route
@app.route('/send-test-email', methods=['POST'])
def send_test_email():
    config = load_config()
    email = config['EMAIL']
    try:
        # Send an email to test the email functionality and settings
        send_email(email, 'Test Email from Temperature Dashboard', 'This is a test email to verify your settings.')
        return jsonify(message='Test email sent successfully', email=email), 200
    except Exception as e:
        return jsonify(error=str(e)), 500


# /login Route
@app.route("/login", methods=["GET", "POST"])
def login():
    # Handle user login, either display the login form or process login credentials
    return login_user()


@app.route("/logout")
def logout():
    return logout_user()

# /settings page for configuring tresholds and email & phone functionality
@app.route('/settings', methods=['GET', 'POST'])
def settings():
    form = SettingsForm(request.form)  # Initialize form for settings
    if request.method == 'POST':
        if form.validate_on_submit():
            # Save the form data if validation is successful
            config_data = {
                'WARNING_TEMP_LOW': form.warning_temp_low.data,
                'WARNING_TEMP_HIGH': form.warning_temp_high.data,
                'CRITICAL_TEMP_LOW': form.critical_temp_low.data,
                'CRITICAL_TEMP_HIGH': form.critical_temp_high.data,
                'EMAIL': form.email.data,
                'PHONE_NUMBER': form.phone_number.data,
            }
            save_config(config_data)
            flash('Settings have been saved successfully.')
            return redirect(url_for('settings'))
        else:
            flash('Error saving settings. Please check your inputs.')
    else:
        # Load existing settings into form fields when loading the settings page
        config_data = load_config()
        form.warning_temp_low.data = config_data.get('WARNING_TEMP_LOW', 25.0)
        form.warning_temp_high.data = config_data.get('WARNING_TEMP_HIGH', 30.0)
        form.critical_temp_low.data = config_data.get('CRITICAL_TEMP_LOW', 30.0)
        form.critical_temp_high.data = config_data.get('CRITICAL_TEMP_HIGH', 35.0)
        form.email.data = config_data.get('EMAIL', 'default-email@example.com')
        form.phone_number.data = config_data.get('PHONE_NUMBER', '+1234567890')
    return render_template('settings.html', form=form)

@app.route("/")
def home():
    
    if "username" not in session:
        # Redirect to login if user is not logged in
        return redirect(url_for("login"))
    
    # set config variable
    config = load_config() 

    # Extracting individual configuration values
    warning_temp_low = config.get('WARNING_TEMP_LOW', float('inf'))  # Provide default values if key might not exist
    warning_temp_high = config.get('WARNING_TEMP_HIGH', float('inf'))
    critical_temp_low = config.get('CRITICAL_TEMP_LOW', float('inf'))
    critical_temp_high = config.get('CRITICAL_TEMP_HIGH', float('inf'))
    
    # Query InfluxDB to retrieve the last 30 days of temperature data
    query = f'from(bucket: "{INFLUXDB_BUCKET}") |> range(start: -30d) |> filter(fn: (r) => r._measurement == "B0A732FFFFF1A160_BLE_0_0_0_E2C4F3FFFF199E64_RuuviTag_0_Temperature") |> filter(fn: (r) => exists r._value)'
    result = query_api.query(org=INFLUXDB_ORG, query=query)


    # Process the results into a DataFrame and sort by timestamp
    data = [
        (record.get_time(), record.get_value())
        for table in result
        for record in table.records
    ]
    df = pd.DataFrame(data, columns=["timestamp", "value"]).sort_values(by="timestamp")
    
    # Initialize placeholders for the last actual and next predicted values
    last_12actual_values = pd.DataFrame(columns=["timestamp", "value"])
    next_12predicted_values = pd.DataFrame(columns=["timestamp", "predicted_value"])

    if not df.empty:
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        last_12actual_values = df.tail(12)  # Get the last 10 actual values

    # Get the current and last predicted values
    current_value = float(df['value'].iloc[-1]) if not df.empty else None
    current_status = evaluate_sensor_status(df, next_12predicted_values, config)
    
    # Check if DataFrame for sensor values is not empty and contains enough data for prediction, then process the data through the prediction model
    if not df.empty and len(df["value"]) >= prediction_model.sequence_length:
        # Extract the last sequence_length values from the DataFrame for input to the model
        input_sequence = df["value"][-prediction_model.sequence_length:].to_numpy()
        # Normalize the extracted input sequence to be within the scale expected by the model
        normalized_input_sequence = prediction_model.normalize(input_sequence)
        # Reshape the normalized data to match the input shape required by the model
        reshaped_input = normalized_input_sequence.reshape(1, prediction_model.sequence_length, 1)
        # Generate predictions using the reshaped input sequence
        predictions = prediction_model.predict(reshaped_input)
        # Create a range of future timestamps for the predicted values, starting 5 minutes after the last available timestamp
        prediction_intervals = pd.date_range(start=df["timestamp"].iloc[-1] + pd.Timedelta(minutes=5), periods=len(predictions), freq="5min")
        # Create a DataFrame to hold the future timestamps and corresponding predicted values
        next_12predicted_values = pd.DataFrame({"timestamp": prediction_intervals, "predicted_value": predictions})

        # Alert for predicted values if current value is normal
        alert_for_predicted_values(next_12predicted_values, current_value, config)

    # Create a Plotly figure and add the actual and predicted
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(x=df["timestamp"], y=df["value"], mode="lines", name="Actual Data")
    )
    
    # If there are predicted values available, add them as a new trace to the Plotly graph
    if not next_12predicted_values.empty:
        fig.add_trace(
            go.Scatter(
                x=next_12predicted_values["timestamp"],
                y=next_12predicted_values["predicted_value"],
                mode="lines",
                name="Predictions",
            )
        )

    
    # Status Checking for sensor
    current_status = "normal"  

    if not df.empty:
        # Check the last recorded value in the dataframe
        last_value = df['value'].iloc[-1]
        # Determine the current status based on temperature thresholds
        current_status = check_current_status(last_value, warning_temp_low, warning_temp_high, critical_temp_low, critical_temp_high)

        # Only check predictions status if current status is normal
        if current_status == "normal":  
            predicted_values = next_12predicted_values['predicted_value'].apply(float).tolist()
            predictive_status = check_proactive_status(predicted_values, warning_temp_low, warning_temp_high, critical_temp_low, critical_temp_high)
            if predictive_status != "normal":
                current_status = predictive_status


    
    # Serialize the plotly figure for rendering in the frontend
    graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    
    # Rename columns for both actual & predicted temp dataframes
    last_12actual_values.rename(columns={'timestamp': 'Timestamp', 'value': 'Value'}, inplace=True)
    next_12predicted_values.rename(columns={'timestamp': 'Timestamp', 'predicted_value': 'Value'}, inplace=True)

    # Format the Timestamp column to be more user-friendly
    last_12actual_values['Timestamp'] = pd.to_datetime(last_12actual_values['Timestamp']).dt.strftime('%Y-%m-%d %H:%M')
    next_12predicted_values['Timestamp'] = pd.to_datetime(next_12predicted_values['Timestamp']).dt.strftime('%Y-%m-%d %H:%M')
    
    # Round the 'Value' column to two decimal places
    last_12actual_values['Value'] = last_12actual_values['Value'].apply(lambda x: '{:.2f}'.format(x))
    next_12predicted_values['Value'] = next_12predicted_values['Value'].apply(lambda x: '{:.2f}'.format(x))
    
    # Convert data frames to HTML if they are not empty
    last_12actual_values_html = last_12actual_values.to_html(classes="table", index=False) if not last_12actual_values.empty else ""
    next_12predicted_values_html = next_12predicted_values.to_html(classes="table", index=False) if not next_12predicted_values.empty else ""
    print(f"Last value: {last_value}")

    # Render the main dashboard page with all components integrated
    return render_template(
        "index.html",
        graphJSON=graphJSON,
        last_12actual_values=last_12actual_values_html,
        next_12predicted_values=next_12predicted_values_html,
        warning_temp_low=warning_temp_low,
        warning_temp_high=warning_temp_high,
        critical_temp_low=critical_temp_low,
        critical_temp_high=critical_temp_high,
        current_status=current_status,
    )
    
# Start the Flask app
if __name__ == "__main__":
    app.run(debug=True)
    