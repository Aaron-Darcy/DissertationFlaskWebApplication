# Alert.py
#Imports
import os
import json
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from twilio.rest import Client
from datetime import datetime, timedelta
from flask_wtf import FlaskForm
from wtforms import StringField, FloatField, SubmitField
from wtforms.validators import DataRequired, Email
from dotenv import load_dotenv
load_dotenv(override=True)


# Twillio/sendgrid keys
SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY')
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')

# Config Path
CONFIG_PATH = 'configs/Config.json'

# Load configuration from JSON file
def load_config():
    try:
        with open(CONFIG_PATH, 'r') as config_file:
            return json.load(config_file)
    except FileNotFoundError:
        print("Configuration file not found", CONFIG_PATH)
        return {}
    except json.JSONDecodeError:
        print("Error loading the JSON configuration file")
        return {}

# Save updated configuration to JSON file
def save_config(config_data):
    with open(CONFIG_PATH, 'w') as config_file:
        json.dump(config_data, config_file, indent=4)

# Function to send an email using SendGrid
def send_email(to_email, subject, message):
    try:
        # Initialize SendGrid API client
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        # Create email message
        email = Mail(
            from_email='aaron.darcy@kelsius.com', 
            to_emails=to_email, 
            subject=subject, 
            plain_text_content=message
        )
        # Send email
        response = sg.send(email)
        print(f"Email sent with status code: {response.status_code}")
    except Exception as e:
        # Handle exceptions if email sending fails
        print(f"Failed to send email: {e}")

# Function to send an SMS using Twilio
def send_sms(to_phone, message):
    try:
        # Initialize Twilio client
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        # Send SMS
        message = client.messages.create(
            body=message, 
            from_='+1234567890', 
            to=to_phone
        )
        print(f"SMS sent; SID: {message.sid}")
    except Exception as e:
        # Handle exceptions if SMS sending fails
        print(f"Failed to send SMS: {e}")

# Function to send both email and SMS alert
def send_alert(email, phone_number, subject, message):
    """Sends an email and an SMS alert."""
    # Send email
    send_email(email, subject, message)
    # Send SMS
    send_sms(phone_number, message)

# Fcuntion to determine if an alert should be sent based on the time elapsed
def should_send_alert(last_alert_time, current_time, alert_interval):
    return (current_time - last_alert_time) >= timedelta(hours=alert_interval)

# Fucntion to check temperature values against configured thresholds and alert if necessary
def check_temperature_and_alert(value, current_time):
    config = load_config()
    email = config.get('EMAIL', 'default-email@example.com')
    phone_number = config.get('PHONE_NUMBER', '+1234567890')
    
    # Define threshold conditions from config
    conditions = {
        'critical_low': config.get('CRITICAL_TEMP_LOW', float('inf')),
        'critical_high': config.get('CRITICAL_TEMP_HIGH', float('inf')),
        'warning_low': config.get('WARNING_TEMP_LOW', float('inf')),
        'warning_high': config.get('WARNING_TEMP_HIGH', float('inf'))
    }
    
    # Check if the value falls outside the critical range
    alert_condition = None
    if value < conditions['critical_low'] or value > conditions['critical_high']:
        alert_condition = 'critical'
    # Check if the value falls within the warning range
    elif conditions['critical_low'] <= value < conditions['warning_low'] or conditions['warning_high'] < value <= conditions['critical_high']:
        alert_condition = 'warning'

    # If an alert condition is triggered
    if alert_condition:
        # Retrieve the last alert time from configuration, defaulting to a past date if not found
        last_alert_time = datetime.strptime(config.get('last_alert_time', '1970-01-01 00:00:00'), '%Y-%m-%d %H:%M:%S')
        # Check if an alert should be sent based on the time elapsed since the last alert
        if should_send_alert(last_alert_time, current_time, 2):
            # Compose alert message
            alert_message = f'Temperature is {alert_condition}: {value}°C'
            # Send alert via email
            send_email(email, f'{alert_condition.title()}: Temperature Alert', alert_message)
            # Send alert via SMS
            send_sms(phone_number, alert_message)
            # Update last alert time and condition in the configuration
            config['last_alert_time'] = current_time.strftime('%Y-%m-%d %H:%M:%S')
            config['last_alert_condition'] = alert_condition
            # Save updated configuration
            save_config(config)


# Check predicted temperature values against configured thresholds and alert if necessary (only if actual value isn't in treshold)
def alert_for_predicted_values(predicted_values_df, current_value, config):
    """Alerts based on predicted values only if the current value is in a safe state."""
    warning_temp_low = config.get('WARNING_TEMP_LOW', float('inf'))
    warning_temp_high = config.get('WARNING_TEMP_HIGH', float('inf'))
    critical_temp_low = config.get('CRITICAL_TEMP_LOW', float('inf'))
    critical_high = config.get('CRITICAL_TEMP_HIGH', float('inf'))

    email = config.get('EMAIL', 'default-email@example.com')
    phone_number = config.get('PHONE_NUMBER', '+1234567890')

    # Check if the current value is already in a warning or critical state
    if not (critical_temp_low <= current_value <= critical_high or
            warning_temp_low <= current_value <= warning_temp_high):
        # If current value is safe, check the predicted values
        for index, row in predicted_values_df.iterrows():
            predicted_value = row['predicted_value']
            if predicted_value < critical_temp_low or predicted_value > critical_high:
                send_alert(email, phone_number,
                           'Critical Temperature Prediction Alert',
                           f'Sensor predicted to go into critical threshold ({predicted_value}°C) within the next hour.')
                break  # Alert once to avoid spamming
            elif predicted_value < warning_temp_low or predicted_value > warning_temp_high:
                send_alert(email, phone_number,
                           'Warning Temperature Prediction Alert',
                           f'Sensor predicted to go into warning threshold ({predicted_value}°C) within the next hour.')
                break  # Alert once to avoid spamming
            
# Function to determine the status of the sensor based on the last recorded value
def check_current_status(value, warning_low, warning_high, critical_low, critical_high):
    # Check if the value falls within the critical thresholds
    if value < critical_low or value > critical_high:
        return "critical"
    # Check if the value falls within the warning thresholds
    elif value < warning_low or value > warning_high:
        return "warning"
    # If value is within normal range
    else:
        return "normal"

# Function to determine the proactive status based on predicted values
def check_proactive_status(predicted_values, warning_low, warning_high, critical_low, critical_high):
    # Iterate over predicted values
    for pv in predicted_values:
        # Check if the predicted value falls within the critical thresholds
        if pv < critical_low or pv > critical_high:
            return "critical_predictive"
        # Check if the predicted value falls within the warning thresholds
        elif pv < warning_low or pv > warning_high:
            return "warning_predictive"
    # If all predicted values are within normal range
    return "normal"

# Function to evaluate the status of the sensor based on historical and predicted data
def evaluate_sensor_status(df, next_12predicted_values, config):
    # Extract temperature thresholds from configuration
    warning_low = float(config.get('WARNING_TEMP_LOW'))
    warning_high = float(config.get('WARNING_TEMP_HIGH'))
    critical_low = float(config.get('CRITICAL_TEMP_LOW'))
    critical_high = float(config.get('CRITICAL_TEMP_HIGH'))

    # Get the last recorded value from the dataframe
    last_value = df['value'].iloc[-1] if not df.empty else float('inf')  # Use 'inf' if there is no data
    # Extract predicted values from the next 12 hours
    predicted_values = [float(pv) for pv in next_12predicted_values['predicted_value']] if not next_12predicted_values.empty else []

    # Check the current status based on the last recorded value
    current_status = check_current_status(last_value, warning_low, warning_high, critical_low, critical_high)
    # If the current status is normal, check for proactive status based on predicted values
    if current_status == "normal":
        current_status = check_proactive_status(predicted_values, warning_low, warning_high, critical_low, critical_high)

    return current_status


# Define a Form for settings configuration
class SettingsForm(FlaskForm):
    warning_temp_low = FloatField('Warning Temperature Low', validators=[DataRequired()])
    warning_temp_high = FloatField('Warning Temperature High', validators=[DataRequired()])
    critical_temp_low = FloatField('Critical Temperature Low', validators=[DataRequired()])
    critical_temp_high = FloatField('Critical Temperature High', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone_number = StringField('Phone Number', validators=[DataRequired()])
    submit = SubmitField('Save Settings')#

